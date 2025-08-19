import json
import logging
from typing import Dict, Any, Optional
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import (
    WhatsAppSession, WhatsAppContact, WhatsAppMessage, 
    WhatsAppBot, WhatsAppBotTrigger, WhatsAppConversation
)
from .services import WhatsAppBusinessService
from .bot_engine import WhatsAppBotEngine

logger = logging.getLogger(__name__)

# Initialize services
whatsapp_service = WhatsAppBusinessService()
bot_engine = WhatsAppBotEngine()

@csrf_exempt
@require_http_methods(["POST"])
def whatsapp_webhook(request, session_name: str):
    """
    Webhook endpoint for receiving WhatsApp messages from WAHA server
    This is the core of real-time message processing
    """
    try:
        # Parse the webhook payload
        payload = json.loads(request.body)
        logger.info(f"Received webhook for session {session_name}: {payload}")
        
        # Extract message data
        message_data = payload.get('data', {})
        message_type = payload.get('type', 'message')
        
        if message_type == 'message':
            return process_incoming_message(session_name, message_data)
        elif message_type == 'status':
            return process_message_status(session_name, message_data)
        elif message_type == 'session':
            return process_session_event(session_name, message_data)
        else:
            logger.warning(f"Unknown webhook type: {message_type}")
            return HttpResponse(status=200)
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return HttpResponse(status=500)

def process_incoming_message(session_name: str, message_data: Dict[str, Any]) -> HttpResponse:
    """Process incoming WhatsApp message and trigger bot responses"""
    try:
        with transaction.atomic():
            # Get or create session
            try:
                session = WhatsAppSession.objects.get(name=session_name)
            except WhatsAppSession.DoesNotExist:
                logger.error(f"Session {session_name} not found")
                return HttpResponse(status=404)
            
            # Extract message details
            contact_number = message_data.get('from', '')
            message_id = message_data.get('id', '')
            message_type = message_data.get('type', 'text')
            content = message_data.get('text', {}).get('body', '') if message_type == 'text' else ''
            timestamp = message_data.get('timestamp', timezone.now())
            
            # Get or create contact
            contact, created = WhatsAppContact.objects.get_or_create(
                phone_number=contact_number,
                defaults={
                    'name': message_data.get('notifyName', 'Unknown'),
                    'status': 'active',
                    'last_interaction': timestamp
                }
            )
            
            if not created:
                contact.last_interaction = timestamp
                contact.total_messages += 1
                contact.save()
            
            # Create message record
            message = WhatsAppMessage.objects.create(
                session=session,
                contact=contact,
                message_id=message_id,
                direction='inbound',
                type=message_type,
                content=content,
                status='delivered',
                sent_at=timestamp
            )
            
            # Get or create conversation
            conversation, conv_created = WhatsAppConversation.objects.get_or_create(
                contact=contact,
                session=session,
                defaults={
                    'status': 'active',
                    'first_message_at': timestamp,
                    'last_message_at': timestamp
                }
            )
            
            if not conv_created:
                conversation.last_message_at = timestamp
                conversation.save()
            
            # Process with bot engine
            bot_response = bot_engine.process_message(
                session=session,
                contact=contact,
                message=message,
                conversation=conversation
            )
            
            # Send bot response if available
            if bot_response:
                whatsapp_service.send_message(
                    session_id=session.session_id,
                    to=contact_number,
                    message=bot_response['content'],
                    message_type=bot_response.get('type', 'text')
                )
                
                # Record bot response
                WhatsAppMessage.objects.create(
                    session=session,
                    contact=contact,
                    message_id=f"bot_{message_id}",
                    direction='outbound',
                    type=bot_response.get('type', 'text'),
                    content=bot_response['content'],
                    status='sent',
                    is_bot_response=True,
                    bot_trigger=bot_response.get('trigger', 'auto'),
                    sent_at=timezone.now()
                )
            
            # Update session activity
            session.messages_received += 1
            session.last_activity = timezone.now()
            session.save()
            
            logger.info(f"Processed incoming message from {contact_number} in session {session_name}")
            return HttpResponse(status=200)
            
    except Exception as e:
        logger.error(f"Error processing incoming message: {e}")
        return HttpResponse(status=500)

def process_message_status(session_name: str, status_data: Dict[str, Any]) -> HttpResponse:
    """Process message delivery status updates"""
    try:
        message_id = status_data.get('id', '')
        status = status_data.get('status', '')
        
        # Update message status in database
        try:
            message = WhatsAppMessage.objects.get(message_id=message_id)
            message.status = status
            
            if status == 'delivered':
                message.delivered_at = timezone.now()
            elif status == 'read':
                message.read_at = timezone.now()
            
            message.save()
            logger.info(f"Updated message {message_id} status to {status}")
            
        except WhatsAppMessage.DoesNotExist:
            logger.warning(f"Message {message_id} not found for status update")
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error processing message status: {e}")
        return HttpResponse(status=500)

def process_session_event(session_name: str, event_data: Dict[str, Any]) -> HttpResponse:
    """Process session lifecycle events"""
    try:
        event_type = event_data.get('event', '')
        
        try:
            session = WhatsAppSession.objects.get(name=session_name)
            
            if event_type == 'connected':
                session.status = 'active'
                session.save()
                logger.info(f"Session {session_name} connected")
            elif event_type == 'disconnected':
                session.status = 'disconnected'
                session.save()
                logger.info(f"Session {session_name} disconnected")
            elif event_type == 'error':
                session.status = 'error'
                session.save()
                logger.error(f"Session {session_name} error: {event_data.get('error', 'Unknown error')}")
                
        except WhatsAppSession.DoesNotExist:
            logger.error(f"Session {session_name} not found for event processing")
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error processing session event: {e}")
        return HttpResponse(status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def test_webhook(request):
    """Test endpoint for webhook functionality"""
    try:
        # Simulate incoming message for testing
        test_data = {
            'type': 'message',
            'data': {
                'from': '+919876543210',
                'id': 'test_message_123',
                'type': 'text',
                'text': {'body': 'Hello, this is a test message'},
                'timestamp': timezone.now().isoformat(),
                'notifyName': 'Test User'
            }
        }
        
        # Process test message
        result = process_incoming_message('test_session', test_data['data'])
        
        return Response({
            'success': True,
            'message': 'Webhook test completed',
            'result': 'success' if result.status_code == 200 else 'failed'
        })
        
    except Exception as e:
        logger.error(f"Webhook test failed: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


