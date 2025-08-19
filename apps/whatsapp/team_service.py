import logging
from typing import Dict, Any, List, Optional, Tuple
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Avg
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import json

from .models import (
    WhatsAppTeamMember, WhatsAppConversation, WhatsAppMessage,
    WhatsAppContact, WhatsAppSession
)

User = get_user_model()
logger = logging.getLogger(__name__)

class WhatsAppTeamService:
    """
    WhatsApp Team Service for real-time collaboration and workload management
    
    Features:
    - Real-time team status tracking
    - Intelligent conversation routing
    - Workload balancing
    - Performance tracking
    - Team collaboration tools
    """
    
    def __init__(self):
        self.max_conversations_per_agent = 5
        self.response_time_threshold = 15  # minutes
    
    def get_team_status(self) -> Dict[str, Any]:
        """Get real-time team status and availability"""
        try:
            team_members = WhatsAppTeamMember.objects.select_related('user').all()
            
            online_members = []
            offline_members = []
            busy_members = []
            
            for member in team_members:
                member_data = {
                    'id': str(member.id),
                    'name': member.user.get_full_name() or member.user.username,
                    'role': member.role,
                    'is_online': member.is_online,
                    'last_seen': member.last_seen.isoformat() if member.last_seen else None,
                    'active_conversations': self._get_active_conversation_count(member),
                    'response_time': member.average_response_time,
                    'satisfaction_score': member.customer_satisfaction_score
                }
                
                if member.is_online:
                    if member_data['active_conversations'] >= self.max_conversations_per_agent:
                        busy_members.append(member_data)
                    else:
                        online_members.append(member_data)
                else:
                    offline_members.append(member_data)
            
            return {
                'success': True,
                'data': {
                    'online_members': online_members,
                    'offline_members': offline_members,
                    'busy_members': busy_members,
                    'total_members': len(team_members),
                    'available_agents': len(online_members),
                    'busy_agents': len(busy_members)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting team status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def route_conversation(self, conversation_id: str, priority: str = 'medium') -> Dict[str, Any]:
        """Route a conversation to the most suitable team member"""
        try:
            with transaction.atomic():
                conversation = WhatsAppConversation.objects.select_for_update().get(id=conversation_id)
                
                # Find the best available agent
                best_agent = self._find_best_agent(conversation, priority)
                
                if not best_agent:
                    return {
                        'success': False,
                        'error': 'No available agents found'
                    }
                
                # Assign conversation to agent
                conversation.assigned_agent = best_agent
                conversation.status = 'active'
                conversation.save()
                
                # Update agent's active conversation count
                self._update_agent_workload(best_agent)
                
                # Send notification to agent (in production, use WebSockets)
                self._notify_agent(best_agent, conversation)
                
                return {
                    'success': True,
                    'message': f'Conversation routed to {best_agent.user.get_full_name()}',
                    'agent_id': str(best_agent.id),
                    'agent_name': best_agent.user.get_full_name()
                }
                
        except WhatsAppConversation.DoesNotExist:
            return {
                'success': False,
                'error': 'Conversation not found'
            }
        except Exception as e:
            logger.error(f"Error routing conversation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _find_best_agent(self, conversation: WhatsAppConversation, priority: str) -> Optional[WhatsAppTeamMember]:
        """Find the best available agent for a conversation"""
        try:
            # Get available agents (online and not at capacity)
            available_agents = WhatsAppTeamMember.objects.filter(
                is_online=True,
                status='active'
            ).annotate(
                active_conversations=Count('assigned_conversations', filter=Q(
                    assigned_conversations__status='active'
                ))
            ).filter(
                active_conversations__lt=self.max_conversations_per_agent
            )
            
            if not available_agents:
                return None
            
            # Score agents based on multiple factors
            agent_scores = []
            
            for agent in available_agents:
                score = self._calculate_agent_score(agent, conversation, priority)
                agent_scores.append((agent, score))
            
            # Sort by score (highest first) and return the best
            agent_scores.sort(key=lambda x: x[1], reverse=True)
            return agent_scores[0][0] if agent_scores else None
            
        except Exception as e:
            logger.error(f"Error finding best agent: {e}")
            return None
    
    def _calculate_agent_score(self, agent: WhatsAppTeamMember, conversation: WhatsAppConversation, 
                              priority: str) -> float:
        """Calculate a score for an agent based on multiple factors"""
        try:
            score = 0.0
            
            # Base score from role and permissions
            role_scores = {
                'admin': 100,
                'manager': 90,
                'agent': 80,
                'sales': 70,
                'marketing': 60,
                'viewer': 0
            }
            score += role_scores.get(agent.role, 50)
            
            # Performance score (0-100)
            if agent.customer_satisfaction_score > 0:
                score += (agent.customer_satisfaction_score / 5.0) * 20
            
            # Response time score (faster is better)
            if agent.average_response_time > 0:
                response_score = max(0, 20 - (agent.average_response_time / 5))
                score += response_score
            
            # Workload score (less busy is better)
            active_conversations = self._get_active_conversation_count(agent)
            workload_score = max(0, 20 - (active_conversations * 4))
            score += workload_score
            
            # Priority matching
            if priority == 'urgent' and agent.role in ['admin', 'manager']:
                score += 30
            elif priority == 'high' and agent.role in ['admin', 'manager', 'agent']:
                score += 20
            
            # Specialization matching (if conversation has tags)
            if conversation.tags:
                agent_tags = agent.working_hours.get('specializations', [])
                if any(tag in agent_tags for tag in conversation.tags):
                    score += 25
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating agent score: {e}")
            return 0.0
    
    def _get_active_conversation_count(self, agent: WhatsAppTeamMember) -> int:
        """Get the number of active conversations for an agent"""
        try:
            return WhatsAppConversation.objects.filter(
                assigned_agent=agent,
                status='active'
            ).count()
        except Exception as e:
            logger.error(f"Error getting active conversation count: {e}")
            return 0
    
    def _update_agent_workload(self, agent: WhatsAppTeamMember):
        """Update agent's workload statistics"""
        try:
            active_conversations = self._get_active_conversation_count(agent)
            
            # Update performance metrics
            if active_conversations > 0:
                # Calculate average response time for recent conversations
                recent_conversations = WhatsAppConversation.objects.filter(
                    assigned_agent=agent,
                    status__in=['active', 'resolved'],
                    last_message_at__gte=timezone.now() - timedelta(days=7)
                )
                
                total_response_time = 0
                response_count = 0
                
                for conv in recent_conversations:
                    messages = WhatsAppMessage.objects.filter(
                        conversation=conv
                    ).order_by('created_at')
                    
                    if messages.count() > 1:
                        first_customer_msg = messages.filter(direction='inbound').first()
                        first_agent_msg = messages.filter(direction='outbound').first()
                        
                        if first_customer_msg and first_agent_msg:
                            response_time = (first_agent_msg.created_at - first_customer_msg.created_at).total_seconds() / 60
                            total_response_time += response_time
                            response_count += 1
                
                if response_count > 0:
                    agent.average_response_time = total_response_time / response_count
                    agent.save()
                    
        except Exception as e:
            logger.error(f"Error updating agent workload: {e}")
    
    def _notify_agent(self, agent: WhatsAppTeamMember, conversation: WhatsAppConversation):
        """Send notification to agent about new conversation assignment"""
        try:
            # In production, this would use WebSockets or push notifications
            # For now, we'll just log the notification
            
            notification_data = {
                'type': 'new_conversation',
                'conversation_id': str(conversation.id),
                'contact_name': conversation.contact.name or conversation.contact.phone_number,
                'priority': conversation.priority,
                'timestamp': timezone.now().isoformat()
            }
            
            logger.info(f"Notification sent to agent {agent.user.username}: {notification_data}")
            
            # You could also create a notification record in the database
            # or send an email/SMS notification
            
        except Exception as e:
            logger.error(f"Error notifying agent: {e}")
    
    def transfer_conversation(self, conversation_id: str, new_agent_id: str, 
                            reason: str = '') -> Dict[str, Any]:
        """Transfer a conversation to a different agent"""
        try:
            with transaction.atomic():
                conversation = WhatsAppConversation.objects.select_for_update().get(id=conversation_id)
                new_agent = WhatsAppTeamMember.objects.get(id=new_agent_id)
                
                # Check if new agent is available
                if not new_agent.is_online or new_agent.status != 'active':
                    return {
                        'success': False,
                        'error': 'New agent is not available'
                    }
                
                active_conversations = self._get_active_conversation_count(new_agent)
                if active_conversations >= self.max_conversations_per_agent:
                    return {
                        'success': False,
                        'error': 'New agent is at capacity'
                    }
                
                # Remove from old agent
                old_agent = conversation.assigned_agent
                if old_agent:
                    self._update_agent_workload(old_agent)
                
                # Assign to new agent
                conversation.assigned_agent = new_agent
                conversation.save()
                
                # Update new agent's workload
                self._update_agent_workload(new_agent)
                
                # Log the transfer
                self._log_conversation_transfer(conversation, old_agent, new_agent, reason)
                
                return {
                    'success': True,
                    'message': f'Conversation transferred to {new_agent.user.get_full_name()}',
                    'old_agent': old_agent.user.get_full_name() if old_agent else None,
                    'new_agent': new_agent.user.get_full_name()
                }
                
        except WhatsAppConversation.DoesNotExist:
            return {
                'success': False,
                'error': 'Conversation not found'
            }
        except WhatsAppTeamMember.DoesNotExist:
            return {
                'success': False,
                'error': 'New agent not found'
            }
        except Exception as e:
            logger.error(f"Error transferring conversation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _log_conversation_transfer(self, conversation: WhatsAppConversation, 
                                  old_agent: Optional[WhatsAppTeamMember],
                                  new_agent: WhatsAppTeamMember, reason: str):
        """Log conversation transfer for audit purposes"""
        try:
            # Create a system message to log the transfer
            transfer_message = f"Conversation transferred from {old_agent.user.get_full_name() if old_agent else 'Unassigned'} to {new_agent.user.get_full_name()}"
            if reason:
                transfer_message += f" - Reason: {reason}"
            
            # You could create a system message record here
            # or log it to a separate audit log
            
            logger.info(f"Conversation {conversation.id} transferred: {transfer_message}")
            
        except Exception as e:
            logger.error(f"Error logging conversation transfer: {e}")
    
    def get_agent_performance(self, agent_id: str, days: int = 30) -> Dict[str, Any]:
        """Get detailed performance metrics for a team member"""
        try:
            agent = WhatsAppTeamMember.objects.get(id=agent_id)
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # Get conversations in the specified period
            conversations = WhatsAppConversation.objects.filter(
                assigned_agent=agent,
                created_at__gte=cutoff_date
            )
            
            # Calculate metrics
            total_conversations = conversations.count()
            resolved_conversations = conversations.filter(status='resolved').count()
            active_conversations = conversations.filter(status='active').count()
            
            # Response time metrics
            response_times = []
            for conv in conversations:
                messages = WhatsAppMessage.objects.filter(conversation=conv).order_by('created_at')
                if messages.count() > 1:
                    first_customer_msg = messages.filter(direction='inbound').first()
                    first_agent_msg = messages.filter(direction='outbound').first()
                    
                    if first_customer_msg and first_agent_msg:
                        response_time = (first_agent_msg.created_at - first_customer_msg.created_at).total_seconds() / 60
                        response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Customer satisfaction
            satisfaction_score = agent.customer_satisfaction_score
            
            return {
                'success': True,
                'data': {
                    'agent_name': agent.user.get_full_name(),
                    'role': agent.role,
                    'period_days': days,
                    'total_conversations': total_conversations,
                    'resolved_conversations': resolved_conversations,
                    'active_conversations': active_conversations,
                    'resolution_rate': (resolved_conversations / total_conversations * 100) if total_conversations > 0 else 0,
                    'average_response_time': round(avg_response_time, 2),
                    'customer_satisfaction': satisfaction_score,
                    'total_messages_sent': agent.total_messages_sent,
                    'total_customers_helped': agent.total_customers_helped
                }
            }
            
        except WhatsAppTeamMember.DoesNotExist:
            return {
                'success': False,
                'error': 'Agent not found'
            }
        except Exception as e:
            logger.error(f"Error getting agent performance: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_agent_status(self, agent_id: str, is_online: bool) -> Dict[str, Any]:
        """Update agent's online/offline status"""
        try:
            agent = WhatsAppTeamMember.objects.get(id=agent_id)
            agent.is_online = is_online
            agent.last_seen = timezone.now()
            agent.save()
            
            return {
                'success': True,
                'message': f'Agent {agent.user.get_full_name()} is now {"online" if is_online else "offline"}',
                'status': 'online' if is_online else 'offline'
            }
            
        except WhatsAppTeamMember.DoesNotExist:
            return {
                'success': False,
                'error': 'Agent not found'
            }
        except Exception as e:
            logger.error(f"Error updating agent status: {e}")
            return {
                'success': False,
                'error': str(e)
            }


