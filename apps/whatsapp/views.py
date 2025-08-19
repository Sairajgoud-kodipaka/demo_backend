from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import json
import logging

from .models import (
    WhatsAppSession, WhatsAppContact, WhatsAppMessage, WhatsAppBot,
    WhatsAppBotTrigger, WhatsAppCampaign, WhatsAppTeamMember,
    WhatsAppConversation, WhatsAppAnalytics
)
from .services import WhatsAppBusinessService
from .webhooks import whatsapp_webhook, test_webhook
from apps.users.permissions import IsRoleAllowed

logger = logging.getLogger(__name__)

# Initialize service
whatsapp_service = WhatsAppBusinessService()

# Custom pagination
class WhatsAppPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# Session Management Views
class WhatsAppSessionListView(generics.ListCreateAPIView):
    """List and create WhatsApp sessions"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    pagination_class = WhatsAppPagination
    
    def get_queryset(self):
        return WhatsAppSession.objects.all().order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        try:
            name = request.data.get('name')
            phone_number = request.data.get('phone_number')
            team_member_id = request.data.get('team_member_id')
            
            if not name or not phone_number:
                return Response({
                    'success': False,
                    'error': 'Name and phone number are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            session = whatsapp_service.create_session(name, phone_number, team_member_id)
            
            if session:
                return Response({
                    'success': True,
                    'data': {
                        'id': str(session.id),
                        'name': session.name,
                        'phone_number': session.phone_number,
                        'status': session.status
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to create session'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error creating WhatsApp session: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WhatsAppSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage individual WhatsApp session"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    queryset = WhatsAppSession.objects.all()
    lookup_field = 'id'
    
    def update(self, request, *args, **kwargs):
        try:
            session = self.get_object()
            
            # Handle status changes
            if 'status' in request.data:
                new_status = request.data['status']
                if new_status == 'active':
                    success = whatsapp_service.start_session(session.session_id)
                    if not success:
                        return Response({
                            'success': False,
                            'error': 'Failed to start session'
                        }, status=status.HTTP_400_BAD_REQUEST)
            
            return super().update(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error updating WhatsApp session: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WhatsAppSessionStatusView(APIView):
    """Get detailed session status from WAHA"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'agent'])]
    
    def get(self, request, session_id):
        try:
            status_info = whatsapp_service.get_session_status(session_id)
            return Response({
                'success': True,
                'data': status_info
            })
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Contact Management Views
class WhatsAppContactListView(generics.ListCreateAPIView):
    """List and create WhatsApp contacts"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'agent', 'sales'])]
    pagination_class = WhatsAppPagination
    
    def get_queryset(self):
        queryset = WhatsAppContact.objects.all()
        
        # Filter by search query
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(phone_number__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Filter by customer type
        customer_type = self.request.query_params.get('customer_type', None)
        if customer_type:
            queryset = queryset.filter(customer_type=customer_type)
        
        # Filter by tags
        tags = self.request.query_params.get('tags', None)
        if tags:
            tag_list = tags.split(',')
            for tag in tag_list:
                queryset = queryset.filter(tags__contains=[tag.strip()])
        
        return queryset.order_by('-last_interaction')
    
    def create(self, request, *args, **kwargs):
        try:
            phone_number = request.data.get('phone_number')
            name = request.data.get('name')
            email = request.data.get('email')
            customer_type = request.data.get('customer_type', 'prospect')
            tags = request.data.get('tags', [])
            
            if not phone_number:
                return Response({
                    'success': False,
                    'error': 'Phone number is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            contact = whatsapp_service.get_or_create_contact(phone_number, name)
            
            # Update additional fields
            if email:
                contact.email = email
            if customer_type:
                contact.customer_type = customer_type
            if tags:
                contact.tags = tags
            contact.save()
            
            return Response({
                'success': True,
                'data': {
                    'id': str(contact.id),
                    'phone_number': contact.phone_number,
                    'name': contact.name,
                    'email': contact.email,
                    'customer_type': contact.customer_type,
                    'tags': contact.tags
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating WhatsApp contact: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WhatsAppContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage individual WhatsApp contact"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'agent', 'sales'])]
    queryset = WhatsAppContact.objects.all()
    lookup_field = 'id'


# Message Management Views
class WhatsAppMessageListView(generics.ListAPIView):
    """List WhatsApp messages with filtering"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'agent'])]
    pagination_class = WhatsAppPagination
    
    def get_queryset(self):
        queryset = WhatsAppMessage.objects.select_related('contact', 'session').all()
        
        # Filter by contact
        contact_id = self.request.query_params.get('contact_id', None)
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)
        
        # Filter by session
        session_id = self.request.query_params.get('session_id', None)
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        # Filter by direction
        direction = self.request.query_params.get('direction', None)
        if direction:
            queryset = queryset.filter(direction=direction)
        
        # Filter by type
        message_type = self.request.query_params.get('type', None)
        if message_type:
            queryset = queryset.filter(type=message_type)
        
        return queryset.order_by('-created_at')


class SendWhatsAppMessageView(APIView):
    """Send WhatsApp message"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'agent', 'sales'])]
    
    def post(self, request):
        try:
            session_id = request.data.get('session_id')
            phone_number = request.data.get('phone_number')
            message = request.data.get('message')
            message_type = request.data.get('type', 'text')
            media_url = request.data.get('media_url')
            team_member_id = request.data.get('team_member_id')
            
            if not session_id or not phone_number or not message:
                return Response({
                    'success': False,
                    'error': 'Session ID, phone number, and message are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            success = whatsapp_service.send_message(
                session_id, phone_number, message, message_type, media_url, team_member_id
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Message sent successfully'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to send message'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Bot Management Views
class WhatsAppBotListView(generics.ListCreateAPIView):
    """List and create WhatsApp bots"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    queryset = WhatsAppBot.objects.all()
    pagination_class = WhatsAppPagination


class WhatsAppBotDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage individual WhatsApp bot"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    queryset = WhatsAppBot.objects.all()
    lookup_field = 'id'


class WhatsAppBotTriggerListView(generics.ListCreateAPIView):
    """List and create bot triggers"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    pagination_class = WhatsAppPagination
    
    def get_queryset(self):
        queryset = WhatsAppBotTrigger.objects.select_related('bot').all()
        
        # Filter by bot
        bot_id = self.request.query_params.get('bot_id', None)
        if bot_id:
            queryset = queryset.filter(bot_id=bot_id)
        
        return queryset.order_by('priority', '-created_at')
    
    def create(self, request, *args, **kwargs):
        try:
            bot_id = request.data.get('bot_id')
            name = request.data.get('name')
            trigger_value = request.data.get('trigger_value')
            response_message = request.data.get('response_message')
            trigger_type = request.data.get('trigger_type', 'keyword')
            
            if not all([bot_id, name, trigger_value, response_message]):
                return Response({
                    'success': False,
                    'error': 'All fields are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            trigger = whatsapp_service.create_bot_trigger(
                bot_id, name, trigger_value, response_message, trigger_type
            )
            
            if trigger:
                return Response({
                    'success': True,
                    'data': {
                        'id': str(trigger.id),
                        'name': trigger.name,
                        'trigger_value': trigger.trigger_value,
                        'response_message': trigger.response_message
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to create trigger'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error creating bot trigger: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Campaign Management Views
class WhatsAppCampaignListView(generics.ListCreateAPIView):
    """List and create WhatsApp campaigns"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'marketing'])]
    queryset = WhatsAppCampaign.objects.all()
    pagination_class = WhatsAppPagination


class WhatsAppCampaignDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage individual WhatsApp campaign"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'marketing'])]
    queryset = WhatsAppCampaign.objects.all()
    lookup_field = 'id'


class SendCampaignView(APIView):
    """Send a marketing campaign"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'marketing'])]
    
    def post(self, request, campaign_id):
        try:
            result = whatsapp_service.send_campaign(campaign_id)
            return Response(result)
        except Exception as e:
            logger.error(f"Error sending campaign: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Team Management Views
class WhatsAppTeamMemberListView(generics.ListCreateAPIView):
    """List and create team members"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    queryset = WhatsAppTeamMember.objects.select_related('user').all()
    pagination_class = WhatsAppPagination


class WhatsAppTeamMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage individual team member"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    queryset = WhatsAppTeamMember.objects.select_related('user').all()
    lookup_field = 'id'


class TeamPerformanceView(APIView):
    """Get team member performance metrics"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def get(self, request, team_member_id):
        try:
            days = int(request.query_params.get('days', 30))
            performance = whatsapp_service.get_team_performance(team_member_id, days)
            
            return Response({
                'success': True,
                'data': performance
            })
        except Exception as e:
            logger.error(f"Error getting team performance: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssignConversationView(APIView):
    """Assign conversation to team member"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def post(self, request):
        try:
            conversation_id = request.data.get('conversation_id')
            team_member_id = request.data.get('team_member_id')
            
            if not conversation_id or not team_member_id:
                return Response({
                    'success': False,
                    'error': 'Conversation ID and team member ID are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            success = whatsapp_service.assign_conversation(conversation_id, team_member_id)
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Conversation assigned successfully'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to assign conversation'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error assigning conversation: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Conversation Management Views
class WhatsAppConversationListView(generics.ListAPIView):
    """List WhatsApp conversations"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'agent'])]
    pagination_class = WhatsAppPagination
    
    def get_queryset(self):
        queryset = WhatsAppConversation.objects.select_related(
            'contact', 'session', 'assigned_agent__user'
        ).all()
        
        # Filter by status
        conversation_status = self.request.query_params.get('status', None)
        if conversation_status:
            queryset = queryset.filter(status=conversation_status)
        
        # Filter by assigned agent
        agent_id = self.request.query_params.get('agent_id', None)
        if agent_id:
            queryset = queryset.filter(assigned_agent_id=agent_id)
        
        # Filter by priority
        priority = self.request.query_params.get('priority', None)
        if priority:
            queryset = queryset.filter(priority=priority)
        
        return queryset.order_by('-last_message_at')


class WhatsAppConversationDetailView(generics.RetrieveUpdateAPIView):
    """Manage individual conversation"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'agent'])]
    queryset = WhatsAppConversation.objects.select_related(
        'contact', 'session', 'assigned_agent__user'
    ).all()
    lookup_field = 'id'


# Analytics Views
class WhatsAppAnalyticsView(APIView):
    """Get WhatsApp analytics and metrics"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def get(self, request):
        try:
            # Get date range
            days = int(request.query_params.get('days', 30))
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get analytics data
            analytics = WhatsAppAnalytics.objects.filter(
                date__range=(start_date, end_date)
            ).order_by('date')
            
            # Calculate summary metrics
            total_messages_sent = sum(a.total_messages_sent for a in analytics)
            total_messages_received = sum(a.total_messages_received for a in analytics)
            total_conversations = WhatsAppConversation.objects.filter(
                created_at__date__range=(start_date, end_date)
            ).count()
            
            # Get active sessions count
            active_sessions = WhatsAppSession.objects.filter(status='active').count()
            
            # Get online team members
            online_members = WhatsAppTeamMember.objects.filter(
                status='active', is_online=True
            ).count()
            
            # Get pending conversations
            pending_conversations = WhatsAppConversation.objects.filter(
                status='active', assigned_agent__isnull=True
            ).count()
            
            return Response({
                'success': True,
                'data': {
                    'period': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'days': days
                    },
                    'summary': {
                        'total_messages_sent': total_messages_sent,
                        'total_messages_received': total_messages_received,
                        'total_conversations': total_conversations,
                        'active_sessions': active_sessions,
                        'online_team_members': online_members,
                        'pending_conversations': pending_conversations
                    },
                    'daily_analytics': [
                        {
                            'date': a.date,
                            'messages_sent': a.total_messages_sent,
                            'messages_received': a.total_messages_received
                        } for a in analytics
                    ]
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting analytics: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Dashboard Views
class WhatsAppDashboardView(APIView):
    """Get WhatsApp dashboard data"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'agent'])]
    
    def get(self, request):
        try:
            # Get recent conversations
            recent_conversations = WhatsAppConversation.objects.select_related(
                'contact', 'assigned_agent__user'
            ).order_by('-last_message_at')[:10]
            
            # Get recent messages
            recent_messages = WhatsAppMessage.objects.select_related(
                'contact', 'session'
            ).order_by('-created_at')[:20]
            
            # Get team members status
            team_members = WhatsAppTeamMember.objects.select_related('user').filter(
                status='active'
            )[:10]
            
            # Get active campaigns
            active_campaigns = WhatsAppCampaign.objects.filter(
                status__in=['active', 'scheduled']
            )[:5]
            
            return Response({
                'success': True,
                'data': {
                    'recent_conversations': [
                        {
                            'id': str(c.id),
                            'contact_name': c.contact.name or c.contact.phone_number,
                            'status': c.status,
                            'priority': c.priority,
                            'last_message_at': c.last_message_at,
                            'assigned_agent': c.assigned_agent.user.get_full_name() if c.assigned_agent else None
                        } for c in recent_conversations
                    ],
                    'recent_messages': [
                        {
                            'id': str(m.id),
                            'contact_name': m.contact.name or m.contact.phone_number,
                            'direction': m.direction,
                            'content': m.content[:100],
                            'created_at': m.created_at,
                            'is_bot_response': m.is_bot_response
                        } for m in recent_messages
                    ],
                    'team_members': [
                        {
                            'id': str(tm.id),
                            'name': tm.user.get_full_name(),
                            'role': tm.role,
                            'is_online': tm.is_online,
                            'last_seen': tm.last_seen
                        } for tm in team_members
                    ],
                    'active_campaigns': [
                        {
                            'id': str(c.id),
                            'name': c.name,
                            'status': c.status,
                            'total_recipients': c.total_recipients,
                            'messages_sent': c.messages_sent
                        } for c in active_campaigns
                    ]
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Webhook endpoint for receiving messages
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def whatsapp_webhook(request, session_name):
    """
    Webhook endpoint for receiving WhatsApp messages from WAHA
    """
    try:
        # Parse the webhook payload
        if request.content_type == 'application/json':
            payload = json.loads(request.body)
        else:
            payload = request.POST.dict()
        
        logger.info(f"WhatsApp webhook received for session {session_name}: {payload}")
        
        # Get session by name
        try:
            session = WhatsAppSession.objects.get(name=session_name)
        except WhatsAppSession.DoesNotExist:
            logger.error(f"Session {session_name} not found")
            return Response({'error': 'Session not found'}, status=400)
        
        event_type = payload.get('event')
        
        if event_type == 'message':
            # Handle incoming message
            message_data = payload.get('payload', {})
            from_number = message_data.get('from')
            message_text = message_data.get('body')
            message_id = message_data.get('id')
            
            if from_number and message_text and message_id:
                # Process the message
                success = whatsapp_service.process_incoming_message(
                    session.session_id, from_number, message_text, message_id
                )
                
                if success:
                    logger.info(f"Processed incoming message from {from_number}")
                else:
                    logger.error(f"Failed to process incoming message from {from_number}")
        
        elif event_type == 'session.status':
            # Handle session status changes
            session_status = payload.get('payload', {})
            logger.info(f"Session {session_name} status changed: {session_status}")
            
            # Update session status in database
            if 'status' in session_status:
                new_status = session_status['status']
                if new_status in ['CONNECTED', 'STARTING']:
                    session.status = WhatsAppSession.Status.ACTIVE
                elif new_status in ['DISCONNECTED', 'STOPPING']:
                    session.status = WhatsAppSession.Status.DISCONNECTED
                elif new_status == 'ERROR':
                    session.status = WhatsAppSession.Status.ERROR
                
                session.save()
        
        return Response({'success': True})
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {str(e)}")
        return Response({'error': str(e)}, status=500)
