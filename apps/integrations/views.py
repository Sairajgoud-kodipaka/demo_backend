from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging

from .whatsapp_service import WhatsAppService, JewelryWhatsAppTemplates
from apps.users.permissions import IsRoleAllowed

logger = logging.getLogger(__name__)


class WhatsAppStatusView(APIView):
    """Get WhatsApp session status"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            whatsapp = WhatsAppService()
            status_info = whatsapp.get_session_status()
            
            return Response({
                'success': True,
                'data': status_info
            })
        except Exception as e:
            logger.error(f"Error getting WhatsApp status: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WhatsAppSessionView(APIView):
    """Start WhatsApp session"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def post(self, request):
        try:
            whatsapp = WhatsAppService()
            success = whatsapp.start_session()
            
            if success:
                return Response({
                    'success': True,
                    'message': 'WhatsApp session started successfully'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to start WhatsApp session'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error starting WhatsApp session: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendWhatsAppMessageView(APIView):
    """Send WhatsApp message to a customer"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            phone = request.data.get('phone')
            message = request.data.get('message')
            message_type = request.data.get('type', 'text')
            
            if not phone or not message:
                return Response({
                    'success': False,
                    'error': 'Phone number and message are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            whatsapp = WhatsAppService()
            
            if message_type == 'text':
                success = whatsapp.send_text_message(phone, message)
            elif message_type == 'image':
                image_url = request.data.get('image_url')
                if not image_url:
                    return Response({
                        'success': False,
                        'error': 'Image URL is required for image messages'
                    }, status=status.HTTP_400_BAD_REQUEST)
                success = whatsapp.send_image_message(phone, image_url, message)
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid message type'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if success:
                return Response({
                    'success': True,
                    'data': {'message': 'WhatsApp message sent successfully'},
                    'message': 'WhatsApp message sent successfully'
                })
            else:
                logger.warning(f"WhatsApp message send returned False for {phone}")
                return Response({
                    'success': False,
                    'error': 'Failed to send WhatsApp message - check WAHA connection and session status'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendBulkWhatsAppView(APIView):
    """Send bulk WhatsApp messages for marketing"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'marketing'])]
    
    def post(self, request):
        try:
            recipients = request.data.get('recipients', [])  # List of phone numbers
            message = request.data.get('message')
            template_type = request.data.get('template_type')
            template_data = request.data.get('template_data', {})
            
            if not recipients or not message:
                return Response({
                    'success': False,
                    'error': 'Recipients and message are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            whatsapp = WhatsAppService()
            sent_count = 0
            failed_count = 0
            
            for phone in recipients:
                # Use template if specified
                if template_type == 'new_collection':
                    final_message = JewelryWhatsAppTemplates.new_collection_launch(
                        customer_name=template_data.get('customer_name', 'Valued Customer'),
                        collection_name=template_data.get('collection_name', 'New Collection'),
                        discount=template_data.get('discount', '10'),
                        store_name=template_data.get('store_name', 'Our Store')
                    )
                elif template_type == 'follow_up':
                    final_message = JewelryWhatsAppTemplates.follow_up_message(
                        customer_name=template_data.get('customer_name', 'Valued Customer'),
                        product_interest=template_data.get('product_interest', 'our jewelry'),
                        salesperson_name=template_data.get('salesperson_name', request.user.first_name)
                    )
                else:
                    final_message = message
                
                if whatsapp.send_text_message(phone, final_message):
                    sent_count += 1
                else:
                    failed_count += 1
            
            return Response({
                'success': True,
                'sent_count': sent_count,
                'failed_count': failed_count,
                'message': f'Bulk WhatsApp campaign completed. Sent: {sent_count}, Failed: {failed_count}'
            })
                
        except Exception as e:
            logger.error(f"Error sending bulk WhatsApp messages: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def whatsapp_webhook(request):
    """
    Webhook endpoint for receiving WhatsApp messages and events from WAHA
    """
    try:
        # Parse the webhook payload
        if request.content_type == 'application/json':
            payload = json.loads(request.body)
        else:
            payload = request.POST.dict()
        
        logger.info(f"WhatsApp webhook received: {payload}")
        
        event_type = payload.get('event')
        session = payload.get('session')
        
        if event_type == 'message':
            # Handle incoming message
            message_data = payload.get('payload', {})
            from_number = message_data.get('from')
            message_text = message_data.get('body')
            
            logger.info(f"Received WhatsApp message from {from_number}: {message_text}")
            
            # You can add logic here to:
            # - Store the message in database
            # - Auto-respond to specific keywords
            # - Notify staff about new messages
            # - Route to customer service
            
        elif event_type == 'session.status':
            # Handle session status changes
            session_status = payload.get('payload', {})
            logger.info(f"WhatsApp session status changed: {session_status}")
            
        return JsonResponse({
            'success': True,
            'message': 'Webhook processed successfully'
        })
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


class WhatsAppTemplatesView(APIView):
    """Get available WhatsApp message templates"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        templates = [
            {
                'id': 'appointment_reminder',
                'name': 'Appointment Reminder',
                'description': 'Send appointment reminders to customers',
                'fields': ['customer_name', 'appointment_date', 'appointment_time', 'store_name']
            },
            {
                'id': 'order_ready',
                'name': 'Order Ready for Pickup',
                'description': 'Notify customers when their order is ready',
                'fields': ['customer_name', 'order_number', 'product_name', 'store_name']
            },
            {
                'id': 'payment_reminder',
                'name': 'Payment Reminder',
                'description': 'Send payment due reminders',
                'fields': ['customer_name', 'amount', 'due_date', 'order_number']
            },
            {
                'id': 'new_collection',
                'name': 'New Collection Launch',
                'description': 'Promote new jewelry collections',
                'fields': ['customer_name', 'collection_name', 'discount', 'store_name']
            },
            {
                'id': 'follow_up',
                'name': 'Follow-up Message',
                'description': 'Follow up with prospects',
                'fields': ['customer_name', 'product_interest', 'salesperson_name']
            }
        ]
        
        return Response({
            'success': True,
            'data': templates
        })