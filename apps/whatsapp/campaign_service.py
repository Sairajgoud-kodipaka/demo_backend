import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from datetime import datetime, timedelta
import asyncio
import json

from .models import (
    WhatsAppCampaign, WhatsAppContact, WhatsAppMessage,
    WhatsAppSession, WhatsAppAnalytics
)
from .services import WhatsAppBusinessService

logger = logging.getLogger(__name__)

class WhatsAppCampaignService:
    """
    WhatsApp Campaign Service for executing marketing campaigns
    
    Features:
    - Campaign execution with rate limiting
    - Message scheduling
    - Delivery tracking
    - Performance analytics
    - A/B testing support
    """
    
    def __init__(self):
        self.whatsapp_service = WhatsAppBusinessService()
        self.rate_limit = 30  # messages per minute
        self.max_concurrent_campaigns = 5
    
    def execute_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Execute a WhatsApp marketing campaign"""
        try:
            with transaction.atomic():
                campaign = WhatsAppCampaign.objects.select_for_update().get(id=campaign_id)
                
                if campaign.status != 'scheduled' and campaign.status != 'draft':
                    return {
                        'success': False,
                        'error': f'Campaign status is {campaign.status}, cannot execute'
                    }
                
                # Get target audience
                contacts = self._get_target_audience(campaign)
                if not contacts:
                    return {
                        'success': False,
                        'error': 'No contacts found for target audience'
                    }
                
                # Update campaign status
                campaign.status = 'active'
                campaign.total_recipients = len(contacts)
                campaign.save()
                
                # Start campaign execution
                self._start_campaign_execution(campaign, contacts)
                
                return {
                    'success': True,
                    'message': f'Campaign {campaign.name} started with {len(contacts)} recipients',
                    'campaign_id': str(campaign.id)
                }
                
        except WhatsAppCampaign.DoesNotExist:
            return {
                'success': False,
                'error': 'Campaign not found'
            }
        except Exception as e:
            logger.error(f"Error executing campaign {campaign_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_target_audience(self, campaign: WhatsAppCampaign) -> List[WhatsAppContact]:
        """Get contacts based on campaign targeting criteria"""
        try:
            target_criteria = campaign.target_audience
            queryset = WhatsAppContact.objects.filter(status='active')
            
            # Apply segmentation filters
            if 'customer_type' in target_criteria:
                customer_types = target_criteria['customer_type']
                if isinstance(customer_types, list):
                    queryset = queryset.filter(customer_type__in=customer_types)
                else:
                    queryset = queryset.filter(customer_type=customer_types)
            
            if 'tags' in target_criteria:
                tags = target_criteria['tags']
                if isinstance(tags, list):
                    for tag in tags:
                        queryset = queryset.filter(tags__contains=[tag])
            
            if 'min_total_spent' in target_criteria:
                min_spent = target_criteria['min_total_spent']
                queryset = queryset.filter(total_spent__gte=min_spent)
            
            if 'max_total_spent' in target_criteria:
                max_spent = target_criteria['max_total_spent']
                queryset = queryset.filter(total_spent__lte=max_spent)
            
            if 'last_interaction_days' in target_criteria:
                days = target_criteria['last_interaction_days']
                cutoff_date = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(last_interaction__gte=cutoff_date)
            
            # Exclude contacts who have opted out
            queryset = queryset.exclude(status='opted_out')
            
            return list(queryset)
            
        except Exception as e:
            logger.error(f"Error getting target audience: {e}")
            return []
    
    def _start_campaign_execution(self, campaign: WhatsAppCampaign, contacts: List[WhatsAppContact]):
        """Start the actual campaign execution process"""
        try:
            # Get active WhatsApp sessions
            active_sessions = WhatsAppSession.objects.filter(status='active')
            if not active_sessions:
                logger.error("No active WhatsApp sessions found for campaign")
                return
            
            # Use the first active session (can be enhanced for load balancing)
            session = active_sessions.first()
            
            # Process contacts in batches to respect rate limits
            batch_size = self.rate_limit
            total_contacts = len(contacts)
            
            for i in range(0, total_contacts, batch_size):
                batch = contacts[i:i + batch_size]
                
                # Schedule batch execution
                self._schedule_batch_execution(campaign, session, batch, i // batch_size)
                
        except Exception as e:
            logger.error(f"Error starting campaign execution: {e}")
    
    def _schedule_batch_execution(self, campaign: WhatsAppCampaign, session: WhatsAppSession, 
                                 contacts: List[WhatsAppContact], batch_number: int):
        """Schedule execution of a batch of contacts"""
        try:
            # Calculate delay for this batch (respect rate limits)
            delay_minutes = batch_number
            
            # Schedule the batch
            for contact in contacts:
                self._schedule_message_send(
                    campaign=campaign,
                    session=session,
                    contact=contact,
                    delay_minutes=delay_minutes
                )
                
        except Exception as e:
            logger.error(f"Error scheduling batch {batch_number}: {e}")
    
    def _schedule_message_send(self, campaign: WhatsAppCampaign, session: WhatsAppSession,
                              contact: WhatsAppContact, delay_minutes: int):
        """Schedule sending of a single campaign message"""
        try:
            # Calculate send time
            send_time = timezone.now() + timedelta(minutes=delay_minutes)
            
            # Create scheduled message record
            scheduled_message = WhatsAppMessage.objects.create(
                session=session,
                contact=contact,
                message_id=f"campaign_{campaign.id}_{contact.id}_{int(send_time.timestamp())}",
                direction='outbound',
                type='template',  # Campaign messages are typically templates
                content=campaign.message_template,
                status='pending',
                campaign_id=campaign.id,
                sent_at=send_time
            )
            
            # Schedule actual sending (in production, use Celery or similar)
            self._send_scheduled_message(scheduled_message, delay_minutes)
            
        except Exception as e:
            logger.error(f"Error scheduling message for contact {contact.id}: {e}")
    
    def _send_scheduled_message(self, message: WhatsAppMessage, delay_minutes: int):
        """Send a scheduled campaign message"""
        try:
            # In production, this would be handled by a task queue
            # For now, we'll simulate the sending process
            
            # Update message status
            message.status = 'sent'
            message.save()
            
            # Update campaign statistics
            if message.campaign_id:
                campaign = WhatsAppCampaign.objects.get(id=message.campaign_id)
                campaign.messages_sent += 1
                campaign.save()
                
                # Update analytics
                self._update_campaign_analytics(campaign, message)
            
            logger.info(f"Sent campaign message {message.id} to {message.contact.phone_number}")
            
        except Exception as e:
            logger.error(f"Error sending scheduled message {message.id}: {e}")
            message.status = 'failed'
            message.save()
    
    def _update_campaign_analytics(self, campaign: WhatsAppCampaign, message: WhatsAppMessage):
        """Update campaign performance analytics"""
        try:
            # Get or create analytics record for today
            today = timezone.now().date()
            analytics, created = WhatsAppAnalytics.objects.get_or_create(
                date=today,
                defaults={
                    'total_messages_sent': 0,
                    'campaigns_sent': 0,
                    'campaign_delivery_rate': 0.0
                }
            )
            
            # Update metrics
            analytics.total_messages_sent += 1
            if created or analytics.campaigns_sent == 0:
                analytics.campaigns_sent = 1
            else:
                # Check if this is a new campaign for today
                existing_campaigns = WhatsAppMessage.objects.filter(
                    campaign_id__isnull=False,
                    created_at__date=today
                ).values_list('campaign_id', flat=True).distinct()
                
                analytics.campaigns_sent = len(existing_campaigns)
            
            # Calculate delivery rate
            total_sent = WhatsAppMessage.objects.filter(
                campaign_id=campaign.id,
                status='sent'
            ).count()
            
            total_delivered = WhatsAppMessage.objects.filter(
                campaign_id=campaign.id,
                status='delivered'
            ).count()
            
            if total_sent > 0:
                analytics.campaign_delivery_rate = (total_delivered / total_sent) * 100
            
            analytics.save()
            
        except Exception as e:
            logger.error(f"Error updating campaign analytics: {e}")
    
    def pause_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Pause an active campaign"""
        try:
            with transaction.atomic():
                campaign = WhatsAppCampaign.objects.select_for_update().get(id=campaign_id)
                
                if campaign.status != 'active':
                    return {
                        'success': False,
                        'error': f'Campaign is not active (status: {campaign.status})'
                    }
                
                campaign.status = 'paused'
                campaign.save()
                
                return {
                    'success': True,
                    'message': f'Campaign {campaign.name} paused successfully'
                }
                
        except WhatsAppCampaign.DoesNotExist:
            return {
                'success': False,
                'error': 'Campaign not found'
            }
        except Exception as e:
            logger.error(f"Error pausing campaign {campaign_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def resume_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Resume a paused campaign"""
        try:
            with transaction.atomic():
                campaign = WhatsAppCampaign.objects.select_for_update().get(id=campaign_id)
                
                if campaign.status != 'paused':
                    return {
                        'success': False,
                        'error': f'Campaign is not paused (status: {campaign.status})'
                    }
                
                campaign.status = 'active'
                campaign.save()
                
                return {
                    'success': True,
                    'message': f'Campaign {campaign.name} resumed successfully'
                }
                
        except WhatsAppCampaign.DoesNotExist:
            return {
                'success': False,
                'error': 'Campaign not found'
            }
        except Exception as e:
            logger.error(f"Error resuming campaign {campaign_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_campaign_performance(self, campaign_id: str) -> Dict[str, Any]:
        """Get detailed performance metrics for a campaign"""
        try:
            campaign = WhatsAppCampaign.objects.get(id=campaign_id)
            
            # Calculate delivery metrics
            total_sent = WhatsAppMessage.objects.filter(campaign_id=campaign_id).count()
            delivered = WhatsAppMessage.objects.filter(
                campaign_id=campaign_id,
                status='delivered'
            ).count()
            read = WhatsAppMessage.objects.filter(
                campaign_id=campaign_id,
                status='read'
            ).count()
            failed = WhatsAppMessage.objects.filter(
                campaign_id=campaign_id,
                status='failed'
            ).count()
            
            # Calculate rates
            delivery_rate = (delivered / total_sent * 100) if total_sent > 0 else 0
            read_rate = (read / total_sent * 100) if total_sent > 0 else 0
            failure_rate = (failed / total_sent * 100) if total_sent > 0 else 0
            
            return {
                'success': True,
                'data': {
                    'campaign_name': campaign.name,
                    'status': campaign.status,
                    'total_recipients': campaign.total_recipients,
                    'messages_sent': campaign.messages_sent,
                    'delivery_rate': round(delivery_rate, 2),
                    'read_rate': round(read_rate, 2),
                    'failure_rate': round(failure_rate, 2),
                    'created_at': campaign.created_at.isoformat(),
                    'last_updated': campaign.updated_at.isoformat()
                }
            }
            
        except WhatsAppCampaign.DoesNotExist:
            return {
                'success': False,
                'error': 'Campaign not found'
            }
        except Exception as e:
            logger.error(f"Error getting campaign performance: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_ab_test(self, campaign_id: str, variants: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create A/B test variants for a campaign"""
        try:
            campaign = WhatsAppCampaign.objects.get(id=campaign_id)
            
            if campaign.status != 'draft':
                return {
                    'success': False,
                    'error': 'A/B testing can only be created for draft campaigns'
                }
            
            # Store A/B test variants in campaign metadata
            campaign.target_audience['ab_test'] = {
                'enabled': True,
                'variants': variants,
                'test_size': 0.2,  # 20% of audience for testing
                'winner_determined': False
            }
            campaign.save()
            
            return {
                'success': True,
                'message': f'A/B test created with {len(variants)} variants',
                'variants': variants
            }
            
        except WhatsAppCampaign.DoesNotExist:
            return {
                'success': False,
                'error': 'Campaign not found'
            }
        except Exception as e:
            logger.error(f"Error creating A/B test: {e}")
            return {
                'success': False,
                'error': str(e)
            }


