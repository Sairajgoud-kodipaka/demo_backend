from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import SupportTicket, TicketMessage, SupportNotification, SupportSettings
from .serializers import (
    SupportTicketSerializer, SupportTicketCreateSerializer, SupportTicketUpdateSerializer,
    SupportTicketSummarySerializer, TicketMessageSerializer, TicketMessageCreateSerializer,
    SupportNotificationSerializer, SupportSettingsSerializer
)
from .services import SupportTicketService


class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing support tickets.
    """
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Platform admins can see all tickets
        if user.role == 'platform_admin':
            queryset = SupportTicket.objects.all()
        # Business admins and managers can only see their tenant's tickets
        elif user.role in ['business_admin', 'manager']:
            queryset = SupportTicket.objects.filter(tenant=user.tenant)
        else:
            queryset = SupportTicket.objects.none()
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        priority_filter = self.request.query_params.get('priority')
        category_filter = self.request.query_params.get('category')
        assigned_to_filter = self.request.query_params.get('assigned_to')
        search = self.request.query_params.get('search')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        if assigned_to_filter:
            queryset = queryset.filter(assigned_to_id=assigned_to_filter)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(summary__icontains=search) | 
                Q(ticket_id__icontains=search)
            )
        
        return queryset.select_related('created_by', 'assigned_to', 'tenant').prefetch_related('messages')

    def get_serializer_class(self):
        if self.action == 'create':
            return SupportTicketCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SupportTicketUpdateSerializer
        elif self.action == 'list':
            return SupportTicketSummarySerializer
        return SupportTicketSerializer

    def perform_create(self, serializer):
        ticket = serializer.save()
        # Create initial system message
        TicketMessage.objects.create(
            ticket=ticket,
            sender=self.request.user,
            content=f"Support ticket created: {ticket.title}",
            is_system_message=True,
            message_type='text'
        )
        # Send notifications to platform admins
        SupportTicketService.notify_platform_admins(ticket)

    def perform_update(self, serializer):
        old_status = self.get_object().status
        ticket = serializer.save()
        
        # Create system message for status changes
        if old_status != ticket.status:
            TicketMessage.objects.create(
                ticket=ticket,
                sender=self.request.user,
                content=f"Ticket status changed from {old_status} to {ticket.status}",
                is_system_message=True,
                message_type='status_update'
            )
            
            # Send notifications based on status change
            if ticket.status == SupportTicket.Status.RESOLVED:
                SupportTicketService.notify_ticket_resolved(ticket)
            elif ticket.status == SupportTicket.Status.CLOSED:
                SupportTicketService.notify_ticket_closed(ticket)

    @action(detail=True, methods=['post'])
    def assign_to_me(self, request, pk=None):
        """Assign ticket to the current platform admin"""
        if request.user.role != 'platform_admin':
            return Response(
                {'error': 'Only platform admins can assign tickets'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        ticket = self.get_object()
        ticket.assigned_to = request.user
        ticket.status = SupportTicket.Status.IN_PROGRESS
        ticket.save()
        
        # Create system message
        TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            content=f"Ticket assigned to {request.user.get_full_name()}",
            is_system_message=True,
            message_type='status_update'
        )
        
        return Response({'message': 'Ticket assigned successfully'})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark ticket as resolved"""
        if request.user.role != 'platform_admin':
            return Response(
                {'error': 'Only platform admins can resolve tickets'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        ticket = self.get_object()
        ticket.status = SupportTicket.Status.RESOLVED
        ticket.resolved_at = timezone.now()
        ticket.save()
        
        # Create system message
        TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            content="Issue has been resolved by Platform Admin. Please confirm if the problem is solved.",
            is_system_message=True,
            message_type='resolution'
        )
        
        # Notify business admin
        SupportTicketService.notify_ticket_resolved(ticket)
        
        return Response({'message': 'Ticket marked as resolved'})

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close the ticket"""
        ticket = self.get_object()
        
        # Only business admin who created the ticket or platform admin can close it
        if (request.user.role == 'business_admin' and ticket.created_by != request.user) and \
           request.user.role != 'platform_admin':
            return Response(
                {'error': 'You can only close tickets you created'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        ticket.status = SupportTicket.Status.CLOSED
        ticket.closed_at = timezone.now()
        ticket.save()
        
        # Create system message
        TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            content="Ticket closed",
            is_system_message=True,
            message_type='status_update'
        )
        
        return Response({'message': 'Ticket closed successfully'})

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """Reopen a resolved ticket"""
        ticket = self.get_object()
        
        # Only business admin who created the ticket can reopen it
        if request.user.role == 'business_admin' and ticket.created_by != request.user:
            return Response(
                {'error': 'You can only reopen tickets you created'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if ticket.status != SupportTicket.Status.RESOLVED:
            return Response(
                {'error': 'Only resolved tickets can be reopened'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ticket.status = SupportTicket.Status.REOPENED
        ticket.save()
        
        # Create system message
        TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            content="Ticket reopened - issue persists",
            is_system_message=True,
            message_type='reopening'
        )
        
        # Notify platform admins
        SupportTicketService.notify_ticket_reopened(ticket)
        
        return Response({'message': 'Ticket reopened successfully'})

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get support dashboard statistics"""
        user = request.user
        
        if user.role == 'platform_admin':
            queryset = SupportTicket.objects.all()
        else:
            queryset = SupportTicket.objects.filter(tenant=user.tenant)
        
        # Calculate stats
        total_tickets = queryset.count()
        open_tickets = queryset.filter(status__in=['open', 'in_progress', 'reopened']).count()
        resolved_today = queryset.filter(
            status='resolved',
            resolved_at__date=timezone.now().date()
        ).count()
        
        # Average response time
        tickets_with_response = queryset.filter(
            messages__sender__role='platform_admin'
        ).distinct()
        
        total_response_time = 0
        response_count = 0
        
        for ticket in tickets_with_response:
            first_response = ticket.messages.filter(
                sender__role='platform_admin'
            ).order_by('created_at').first()
            
            if first_response:
                response_time = first_response.created_at - ticket.created_at
                total_response_time += response_time.total_seconds()
                response_count += 1
        
        avg_response_hours = round(total_response_time / 3600 / response_count, 2) if response_count > 0 else 0
        
        # Priority breakdown
        priority_stats = queryset.values('priority').annotate(count=Count('id'))
        
        return Response({
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'resolved_today': resolved_today,
            'avg_response_hours': avg_response_hours,
            'priority_breakdown': priority_stats
        })


class TicketMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ticket messages.
    """
    queryset = TicketMessage.objects.all()
    serializer_class = TicketMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = TicketMessage.objects.all()
        
        # Filter by ticket if specified
        ticket_id = self.request.query_params.get('ticket')
        if ticket_id:
            # Try to filter by numeric ID first, then by ticket_id string
            try:
                ticket_id_int = int(ticket_id)
                queryset = queryset.filter(ticket_id=ticket_id_int)
            except ValueError:
                # If not a number, try filtering by ticket_id string
                queryset = queryset.filter(ticket__ticket_id=ticket_id)
        
        if user.role == 'platform_admin':
            return queryset.select_related('sender', 'ticket', 'ticket__tenant')
        else:
            # Business admins and managers can only see messages from their tenant's tickets
            # and not internal messages
            return queryset.filter(
                ticket__tenant=user.tenant,
                is_internal=False
            ).select_related('sender', 'ticket', 'ticket__tenant')

    def get_serializer_class(self):
        if self.action == 'create':
            return TicketMessageCreateSerializer
        return TicketMessageSerializer

    def perform_create(self, serializer):
        message = serializer.save()
        
        # Send notification to the other party
        ticket = message.ticket
        if message.sender.role == 'platform_admin':
            # Notify business admin
            SupportTicketService.notify_message_received(ticket, message, ticket.created_by)
        else:
            # Notify platform admins
            SupportTicketService.notify_message_received(ticket, message, None)


class SupportNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing support notifications.
    """
    serializer_class = SupportNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SupportNotification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        SupportNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'message': 'All notifications marked as read'})


class SupportSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing support settings.
    """
    serializer_class = SupportSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'platform_admin':
            return SupportSettings.objects.all()
        else:
            return SupportSettings.objects.filter(tenant=user.tenant)

    def perform_create(self, serializer):
        serializer.save() 