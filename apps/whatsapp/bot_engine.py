import re
import logging
from typing import Dict, Any, Optional, List
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    WhatsAppBot, WhatsAppBotTrigger, WhatsAppMessage,
    WhatsAppSession, WhatsAppContact, WhatsAppConversation
)

logger = logging.getLogger(__name__)

class WhatsAppBotEngine:
    """
    WhatsApp Bot Engine for automated message processing
    
    Features:
    - Keyword-based triggers
    - Intent recognition
    - Conversation flow management
    - Human handoff logic
    - Business hours handling
    - Multi-language support
    """
    
    def __init__(self):
        self.default_triggers = {
            'hello': {
                'response': 'Hello! Welcome to our jewelry store. How can I help you today?',
                'type': 'text',
                'requires_human': False
            },
            'help': {
                'response': 'I can help you with:\n• Product information\n• Pricing\n• Store hours\n• Appointments\n• Customer support\n\nWhat would you like to know?',
                'type': 'text',
                'requires_human': False
            },
            'pricing': {
                'response': 'Our jewelry prices vary based on design and materials. Would you like me to connect you with a sales representative for detailed pricing?',
                'type': 'text',
                'requires_human': True
            },
            'appointment': {
                'response': 'I can help you schedule an appointment. Please let me know your preferred date and time, and I\'ll connect you with our team.',
                'type': 'text',
                'requires_human': True
            }
        }
    
    def process_message(self, session: WhatsAppSession, contact: WhatsAppContact, 
                       message: WhatsAppMessage, conversation: WhatsAppConversation) -> Optional[Dict[str, Any]]:
        """
        Process incoming message and generate appropriate response
        
        Returns:
            Dict with response details or None if no response needed
        """
        try:
            # Check if conversation should be handled by human
            if self._should_handoff_to_human(conversation, message):
                return self._create_handoff_response(conversation)
            
            # Check business hours
            if not self._is_business_hours(session):
                return self._create_after_hours_response(session)
            
            # Process with bot triggers
            bot_response = self._process_with_bots(session, contact, message, conversation)
            if bot_response:
                return bot_response
            
            # Check default triggers
            default_response = self._check_default_triggers(message.content)
            if default_response:
                return default_response
            
            # Fallback response
            return self._create_fallback_response(conversation)
            
        except Exception as e:
            logger.error(f"Error processing message with bot engine: {e}")
            return None
    
    def _should_handoff_to_human(self, conversation: WhatsAppConversation, message: WhatsAppMessage) -> bool:
        """Determine if conversation should be handed off to human agent"""
        
        # Check conversation length
        message_count = WhatsAppMessage.objects.filter(
            conversation=conversation
        ).count()
        
        if message_count > 10:  # Too many messages, handoff
            return True
        
        # Check for urgent keywords
        urgent_keywords = ['urgent', 'emergency', 'complaint', 'problem', 'issue']
        if any(keyword in message.content.lower() for keyword in urgent_keywords):
            return True
        
        # Check conversation age
        if conversation.first_message_at < timezone.now() - timedelta(hours=24):
            return True
        
        # Check if customer explicitly requested human
        human_request_keywords = ['human', 'agent', 'representative', 'speak to someone']
        if any(keyword in message.content.lower() for keyword in human_request_keywords):
            return True
        
        return False
    
    def _is_business_hours(self, session: WhatsAppSession) -> bool:
        """Check if current time is within business hours"""
        if not session.business_hours_enabled:
            return True
        
        current_time = timezone.now().time()
        start_time = session.business_hours_start
        end_time = session.business_hours_end
        
        if start_time and end_time:
            return start_time <= current_time <= end_time
        
        return True
    
    def _process_with_bots(self, session: WhatsAppSession, contact: WhatsAppContact,
                          message: WhatsAppMessage, conversation: WhatsAppConversation) -> Optional[Dict[str, Any]]:
        """Process message using configured bot triggers"""
        try:
            # Get active bots for this session
            active_bots = WhatsAppBot.objects.filter(status='active')
            
            for bot in active_bots:
                # Check bot triggers
                triggers = WhatsAppBotTrigger.objects.filter(
                    bot=bot,
                    is_active=True
                ).order_by('priority')
                
                for trigger in triggers:
                    if self._matches_trigger(trigger, message.content):
                        return {
                            'content': trigger.response_message,
                            'type': trigger.response_type,
                            'media_url': trigger.media_url,
                            'trigger': trigger.name,
                            'requires_human': trigger.requires_human_handoff
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing with bots: {e}")
            return None
    
    def _matches_trigger(self, trigger: WhatsAppBotTrigger, message_content: str) -> bool:
        """Check if message matches a bot trigger"""
        try:
            content = message_content.lower().strip()
            trigger_value = trigger.trigger_value.lower().strip()
            
            if trigger.trigger_type == 'exact_match':
                return content == trigger_value
            
            elif trigger.trigger_type == 'keyword':
                keywords = [kw.strip() for kw in trigger_value.split(',')]
                return any(keyword in content for keyword in keywords)
            
            elif trigger.trigger_type == 'regex':
                try:
                    pattern = re.compile(trigger_value, re.IGNORECASE)
                    return bool(pattern.search(content))
                except re.error:
                    logger.warning(f"Invalid regex pattern: {trigger_value}")
                    return False
            
            elif trigger.trigger_type == 'intent':
                # Simple intent recognition based on keywords
                intent_keywords = {
                    'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon'],
                    'farewell': ['bye', 'goodbye', 'see you', 'take care'],
                    'thanks': ['thank you', 'thanks', 'appreciate'],
                    'pricing': ['price', 'cost', 'how much', 'pricing'],
                    'appointment': ['book', 'schedule', 'appointment', 'meeting'],
                    'product': ['product', 'item', 'jewelry', 'ring', 'necklace'],
                    'support': ['help', 'support', 'issue', 'problem']
                }
                
                if trigger_value in intent_keywords:
                    return any(keyword in content for keyword in intent_keywords[trigger_value])
            
            return False
            
        except Exception as e:
            logger.error(f"Error matching trigger: {e}")
            return False
    
    def _check_default_triggers(self, message_content: str) -> Optional[Dict[str, Any]]:
        """Check message against default triggers"""
        content = message_content.lower().strip()
        
        for keyword, response in self.default_triggers.items():
            if keyword in content:
                return {
                    'content': response['response'],
                    'type': response['type'],
                    'requires_human': response['requires_human']
                }
        
        return None
    
    def _create_handoff_response(self, conversation: WhatsAppConversation) -> Dict[str, Any]:
        """Create response for human handoff"""
        return {
            'content': 'I understand you need more personalized assistance. Let me connect you with one of our team members who will be with you shortly. Thank you for your patience!',
            'type': 'text',
            'requires_human': True
        }
    
    def _create_after_hours_response(self, session: WhatsAppSession) -> Dict[str, Any]:
        """Create response for after business hours"""
        if session.after_hours_message:
            return {
                'content': session.after_hours_message,
                'type': 'text',
                'requires_human': False
            }
        else:
            return {
                'content': 'Thank you for your message! We are currently outside of business hours. Our team will respond to you during our next business day. For urgent matters, please call our emergency line.',
                'type': 'text',
                'requires_human': False
            }
    
    def _create_fallback_response(self, conversation: WhatsAppConversation) -> Dict[str, Any]:
        """Create fallback response when no triggers match"""
        return {
            'content': 'Thank you for your message! I\'m here to help, but I want to make sure I understand your request correctly. Could you please rephrase or let me know if you need to speak with a team member?',
            'type': 'text',
            'requires_human': False
        }
    
    def create_bot_trigger(self, bot_id: str, name: str, trigger_type: str, 
                          trigger_value: str, response_message: str, **kwargs) -> Optional[WhatsAppBotTrigger]:
        """Create a new bot trigger"""
        try:
            bot = WhatsAppBot.objects.get(id=bot_id)
            
            trigger = WhatsAppBotTrigger.objects.create(
                bot=bot,
                name=name,
                trigger_type=trigger_type,
                trigger_value=trigger_value,
                response_message=response_message,
                **kwargs
            )
            
            logger.info(f"Created bot trigger: {name} for bot: {bot.name}")
            return trigger
            
        except WhatsAppBot.DoesNotExist:
            logger.error(f"Bot {bot_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error creating bot trigger: {e}")
            return None
    
    def update_conversation_priority(self, conversation: WhatsAppConversation, 
                                   new_priority: str) -> bool:
        """Update conversation priority based on content analysis"""
        try:
            # Analyze recent messages for priority indicators
            recent_messages = WhatsAppMessage.objects.filter(
                conversation=conversation
            ).order_by('-created_at')[:5]
            
            priority_score = 0
            
            for msg in recent_messages:
                if msg.direction == 'inbound':
                    content = msg.content.lower()
                    
                    # High priority indicators
                    if any(word in content for word in ['urgent', 'emergency', 'asap', 'immediately']):
                        priority_score += 3
                    elif any(word in content for word in ['complaint', 'problem', 'issue', 'broken']):
                        priority_score += 2
                    elif any(word in content for word in ['expensive', 'premium', 'vip']):
                        priority_score += 1
            
            # Determine new priority
            if priority_score >= 3:
                new_priority = 'urgent'
            elif priority_score >= 2:
                new_priority = 'high'
            elif priority_score >= 1:
                new_priority = 'medium'
            else:
                new_priority = 'low'
            
            conversation.priority = new_priority
            conversation.save()
            
            logger.info(f"Updated conversation {conversation.id} priority to {new_priority}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating conversation priority: {e}")
            return False


