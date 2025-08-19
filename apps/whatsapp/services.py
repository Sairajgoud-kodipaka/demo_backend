import requests
import json
import re
from typing import Optional, Dict, Any, List, Tuple
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
import logging

from .models import (
    WhatsAppSession, WhatsAppContact, WhatsAppMessage, WhatsAppBot,
    WhatsAppBotTrigger, WhatsAppCampaign, WhatsAppTeamMember,
    WhatsAppConversation, WhatsAppAnalytics
)

logger = logging.getLogger(__name__)

class WhatsAppBusinessService:
    """
    Enhanced WhatsApp Business service with team management, bot automation,
    and campaign features built on top of WAHA server
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'WAHA_BASE_URL', 'http://localhost:3000')
        self.api_key = getattr(settings, 'WAHA_API_KEY', None)
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for WAHA API requests"""
        headers = {
            'Content-Type': 'application/json',
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for WhatsApp (add @c.us suffix)"""
        phone = ''.join(filter(str.isdigit, phone))
        if not phone.startswith('91') and len(phone) == 10:
            phone = '91' + phone
        return f"{phone}@c.us"
    
    # Session Management
    def create_session(self, name: str, phone_number: str, team_member_id: Optional[str] = None) -> Optional[WhatsAppSession]:
        """Create a new WhatsApp session"""
        try:
            # Create session in WAHA
            payload = {
                "name": name,
                "config": {
                    "webhooks": {
                        "url": f"{settings.BASE_URL}/api/whatsapp/webhook/{name}/"
                    }
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/sessions",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                session_data = response.json()
                session_id = session_data.get('id')
                
                # Create session in our database
                session = WhatsAppSession.objects.create(
                    name=name,
                    phone_number=phone_number,
                    session_id=session_id,
                    status=WhatsAppSession.Status.CONNECTING
                )
                
                if team_member_id:
                    try:
                        team_member = WhatsAppTeamMember.objects.get(id=team_member_id)
                        session.assigned_team_member = team_member.user
                        session.save()
                    except WhatsAppTeamMember.DoesNotExist:
                        pass
                
                return session
            else:
                logger.error(f"Failed to create WAHA session: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating WhatsApp session: {str(e)}")
            return None
    
    def start_session(self, session_id: str) -> bool:
        """Start a WhatsApp session"""
        try:
            response = requests.post(
                f"{self.base_url}/api/sessions/{session_id}/start",
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                # Update session status
                try:
                    session = WhatsAppSession.objects.get(session_id=session_id)
                    session.status = WhatsAppSession.Status.ACTIVE
                    session.save()
                    return True
                except WhatsAppSession.DoesNotExist:
                    pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error starting WhatsApp session: {str(e)}")
            return False
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get session status from WAHA"""
        try:
            response = requests.get(
                f"{self.base_url}/api/sessions/{session_id}",
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            return {"error": str(e)}
    
    # Contact Management
    def get_or_create_contact(self, phone_number: str, name: Optional[str] = None) -> WhatsAppContact:
        """Get existing contact or create new one"""
        contact, created = WhatsAppContact.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'name': name,
                'status': WhatsAppContact.Status.ACTIVE
            }
        )
        
        if not created and name and name != contact.name:
            contact.name = name
            contact.save()
        
        return contact
    
    def update_contact_tags(self, contact_id: str, tags: List[str]) -> bool:
        """Update contact tags for segmentation"""
        try:
            contact = WhatsAppContact.objects.get(id=contact_id)
            contact.tags = tags
            contact.save()
            return True
        except WhatsAppContact.DoesNotExist:
            return False
    
    # Message Handling
    def send_message(self, session_id: str, phone_number: str, message: str, 
                    message_type: str = 'text', media_url: Optional[str] = None,
                    team_member_id: Optional[str] = None) -> bool:
        """Send message via WhatsApp"""
        try:
            # Get or create contact
            contact = self.get_or_create_contact(phone_number)
            chat_id = self._format_phone_number(phone_number)
            
            # Prepare payload based on message type
            if message_type == 'text':
                payload = {
                    "session": session_id,
                    "chatId": chat_id,
                    "text": message
                }
                endpoint = "/api/sendText"
            elif message_type == 'image':
                payload = {
                    "session": session_id,
                    "chatId": chat_id,
                    "image": media_url,
                    "caption": message
                }
                endpoint = "/api/sendImage"
            else:
                logger.error(f"Unsupported message type: {message_type}")
                return False
            
            # Send via WAHA
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                # Store message in database
                message_obj = WhatsAppMessage.objects.create(
                    session_id=session_id,
                    contact=contact,
                    direction=WhatsAppMessage.Direction.OUTBOUND,
                    type=message_type,
                    content=message,
                    media_url=media_url,
                    status=WhatsAppMessage.Status.SENT
                )
                
                # Update contact stats
                contact.total_messages += 1
                contact.last_interaction = timezone.now()
                contact.save()
                
                # Update session stats
                try:
                    session = WhatsAppSession.objects.get(session_id=session_id)
                    session.messages_sent += 1
                    session.last_activity = timezone.now()
                    session.save()
                except WhatsAppSession.DoesNotExist:
                    pass
                
                # Update team member stats if provided
                if team_member_id:
                    try:
                        team_member = WhatsAppTeamMember.objects.get(id=team_member_id)
                        team_member.total_messages_sent += 1
                        team_member.save()
                    except WhatsAppTeamMember.DoesNotExist:
                        pass
                
                return True
            else:
                logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return False
    
    def process_incoming_message(self, session_id: str, from_number: str, 
                               message_text: str, message_id: str) -> bool:
        """Process incoming message and trigger bot if needed"""
        try:
            # Get or create contact
            contact = self.get_or_create_contact(from_number)
            
            # Store incoming message
            message_obj = WhatsAppMessage.objects.create(
                session_id=session_id,
                contact=contact,
                direction=WhatsAppMessage.Direction.INBOUND,
                type=WhatsAppMessage.Type.TEXT,
                content=message_text,
                message_id=message_id,
                status=WhatsAppMessage.Status.DELIVERED
            )
            
            # Update contact stats
            contact.total_messages += 1
            contact.last_interaction = timezone.now()
            contact.save()
            
            # Update session stats
            try:
                session = WhatsAppSession.objects.get(session_id=session_id)
                session.messages_received += 1
                session.last_activity = timezone.now()
                session.save()
            except WhatsAppSession.DoesNotExist:
                pass
            
            # Check if bot should respond
            bot_response = self._check_bot_triggers(session_id, message_text, contact)
            if bot_response:
                # Send bot response
                self.send_message(session_id, from_number, bot_response, 'text')
                
                # Mark original message as bot response
                message_obj.is_bot_response = True
                message_obj.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing incoming message: {str(e)}")
            return False
    
    # Bot Automation
    def _check_bot_triggers(self, session_id: str, message_text: str, contact: WhatsAppContact) -> Optional[str]:
        """Check if message triggers any bot responses"""
        try:
            # Get active bot for this session
            session = WhatsAppSession.objects.get(session_id=session_id)
            
            # Check if bot is enabled
            if not session.auto_reply_enabled:
                return None
            
            # Get active bot triggers
            triggers = WhatsAppBotTrigger.objects.filter(
                is_active=True
            ).order_by('priority')
            
            for trigger in triggers:
                if self._matches_trigger(trigger, message_text):
                    return trigger.response_message
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking bot triggers: {str(e)}")
            return None
    
    def _matches_trigger(self, trigger: WhatsAppBotTrigger, message_text: str) -> bool:
        """Check if message matches trigger conditions"""
        try:
            if trigger.trigger_type == WhatsAppBotTrigger.TriggerType.KEYWORD:
                return trigger.trigger_value.lower() in message_text.lower()
            elif trigger.trigger_type == WhatsAppBotTrigger.TriggerType.EXACT_MATCH:
                return trigger.trigger_value.lower() == message_text.lower()
            elif trigger.trigger_type == WhatsAppBotTrigger.TriggerType.REGEX:
                return bool(re.search(trigger.trigger_value, message_text, re.IGNORECASE))
            else:
                return False
        except Exception as e:
            logger.error(f"Error matching trigger: {str(e)}")
            return False
    
    def create_bot_trigger(self, bot_id: str, name: str, trigger_value: str, 
                          response_message: str, trigger_type: str = 'keyword') -> Optional[WhatsAppBotTrigger]:
        """Create a new bot trigger"""
        try:
            trigger = WhatsAppBotTrigger.objects.create(
                bot_id=bot_id,
                name=name,
                trigger_value=trigger_value,
                response_message=response_message,
                trigger_type=trigger_type
            )
            return trigger
        except Exception as e:
            logger.error(f"Error creating bot trigger: {str(e)}")
            return None
    
    # Campaign Management
    def send_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Send a marketing campaign"""
        try:
            campaign = WhatsAppCampaign.objects.get(id=campaign_id)
            
            if campaign.status != WhatsAppCampaign.Status.ACTIVE:
                return {"success": False, "error": "Campaign is not active"}
            
            # Get target audience
            target_contacts = self._get_campaign_recipients(campaign.target_audience)
            
            if not target_contacts:
                return {"success": False, "error": "No recipients found"}
            
            # Update campaign stats
            campaign.total_recipients = len(target_contacts)
            campaign.save()
            
            # Send messages
            sent_count = 0
            failed_count = 0
            
            for contact in target_contacts:
                # Get active session
                session = WhatsAppSession.objects.filter(status=WhatsAppSession.Status.ACTIVE).first()
                if not session:
                    failed_count += 1
                    continue
                
                # Send message
                success = self.send_message(
                    session.session_id,
                    contact.phone_number,
                    campaign.message_template,
                    'text'
                )
                
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
            
            # Update campaign statistics
            campaign.messages_sent = sent_count
            campaign.save()
            
            return {
                "success": True,
                "sent": sent_count,
                "failed": failed_count,
                "total": len(target_contacts)
            }
            
        except WhatsAppCampaign.DoesNotExist:
            return {"success": False, "error": "Campaign not found"}
        except Exception as e:
            logger.error(f"Error sending campaign: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _get_campaign_recipients(self, target_audience: Dict[str, Any]) -> List[WhatsAppContact]:
        """Get contacts based on campaign targeting criteria"""
        try:
            contacts = WhatsAppContact.objects.filter(status=WhatsAppContact.Status.ACTIVE)
            
            # Apply filters based on target audience criteria
            if 'customer_type' in target_audience:
                contacts = contacts.filter(customer_type__in=target_audience['customer_type'])
            
            if 'tags' in target_audience:
                # Filter by tags (JSON field contains)
                for tag in target_audience['tags']:
                    contacts = contacts.filter(tags__contains=[tag])
            
            if 'min_orders' in target_audience:
                contacts = contacts.filter(total_orders__gte=target_audience['min_orders'])
            
            if 'min_spent' in target_audience:
                contacts = contacts.filter(total_spent__gte=target_audience['min_spent'])
            
            return list(contacts)
            
        except Exception as e:
            logger.error(f"Error getting campaign recipients: {str(e)}")
            return []
    
    # Team Management
    def assign_conversation(self, conversation_id: str, team_member_id: str) -> bool:
        """Assign conversation to team member"""
        try:
            conversation = WhatsAppConversation.objects.get(id=conversation_id)
            team_member = WhatsAppTeamMember.objects.get(id=team_member_id)
            
            conversation.assigned_agent = team_member
            conversation.save()
            
            return True
            
        except (WhatsAppConversation.DoesNotExist, WhatsAppTeamMember.DoesNotExist):
            return False
    
    def get_team_performance(self, team_member_id: str, days: int = 30) -> Dict[str, Any]:
        """Get team member performance metrics"""
        try:
            team_member = WhatsAppTeamMember.objects.get(id=team_member_id)
            
            # Calculate date range
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # Get messages sent in date range
            messages_sent = WhatsAppMessage.objects.filter(
                session__assigned_team_member=team_member.user,
                direction=WhatsAppMessage.Direction.OUTBOUND,
                created_at__range=(start_date, end_date)
            ).count()
            
            # Get conversations handled
            conversations_handled = WhatsAppConversation.objects.filter(
                assigned_agent=team_member,
                status=WhatsAppConversation.Status.RESOLVED,
                updated_at__range=(start_date, end_date)
            ).count()
            
            # Calculate average response time
            response_times = []
            conversations = WhatsAppConversation.objects.filter(
                assigned_agent=team_member,
                status=WhatsAppConversation.Status.RESOLVED
            )
            
            for conv in conversations:
                if conv.resolution_time:
                    response_times.append(conv.resolution_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                "messages_sent": messages_sent,
                "conversations_handled": conversations_handled,
                "average_response_time": avg_response_time,
                "customer_satisfaction": team_member.customer_satisfaction_score
            }
            
        except WhatsAppTeamMember.DoesNotExist:
            return {}
    
    # Analytics
    def update_daily_analytics(self, date: datetime.date) -> bool:
        """Update daily analytics for the specified date"""
        try:
            # Get or create analytics record
            analytics, created = WhatsAppAnalytics.objects.get_or_create(date=date)
            
            # Calculate message statistics
            start_datetime = datetime.combine(date, datetime.min.time())
            end_datetime = datetime.combine(date, datetime.max.time())
            
            messages_sent = WhatsAppMessage.objects.filter(
                direction=WhatsAppMessage.Direction.OUTBOUND,
                created_at__range=(start_datetime, end_datetime)
            ).count()
            
            messages_received = WhatsAppMessage.objects.filter(
                direction=WhatsAppMessage.Direction.INBOUND,
                created_at__range=(start_datetime, end_datetime)
            ).count()
            
            # Update analytics
            analytics.total_messages_sent = messages_sent
            analytics.total_messages_received = messages_received
            analytics.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating daily analytics: {str(e)}")
            return False
    
    # Utility Methods
    def get_active_sessions(self) -> List[WhatsAppSession]:
        """Get all active WhatsApp sessions"""
        return WhatsAppSession.objects.filter(status=WhatsAppSession.Status.ACTIVE)
    
    def get_online_team_members(self) -> List[WhatsAppTeamMember]:
        """Get currently online team members"""
        return WhatsAppTeamMember.objects.filter(
            status=WhatsAppTeamMember.Status.ACTIVE,
            is_online=True
        )
    
    def get_pending_conversations(self) -> List[WhatsAppConversation]:
        """Get conversations waiting for assignment"""
        return WhatsAppConversation.objects.filter(
            status=WhatsAppConversation.Status.ACTIVE,
            assigned_agent__isnull=True
        ).order_by('-created_at')
