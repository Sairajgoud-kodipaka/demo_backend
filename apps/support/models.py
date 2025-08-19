from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class SupportTicket(models.Model):
    """
    Support ticket model for handling business admin issues and platform admin responses.
    """
    class Priority(models.TextChoices):
        LOW = 'low', _('Low')
        MEDIUM = 'medium', _('Medium')
        HIGH = 'high', _('High')
        CRITICAL = 'critical', _('Critical')

    class Status(models.TextChoices):
        OPEN = 'open', _('Open')
        IN_PROGRESS = 'in_progress', _('In Progress')
        RESOLVED = 'resolved', _('Resolved')
        CLOSED = 'closed', _('Closed')
        REOPENED = 'reopened', _('Reopened')

    class Category(models.TextChoices):
        TECHNICAL = 'technical', _('Technical Issue')
        BILLING = 'billing', _('Billing & Subscription')
        FEATURE_REQUEST = 'feature_request', _('Feature Request')
        BUG_REPORT = 'bug_report', _('Bug Report')
        GENERAL = 'general', _('General Inquiry')
        INTEGRATION = 'integration', _('Integration Issue')

    # Ticket identification
    ticket_id = models.CharField(max_length=20, unique=True, help_text=_('Unique ticket identifier'))
    title = models.CharField(max_length=200, help_text=_('Brief description of the issue'))
    summary = models.TextField(help_text=_('Detailed description of the issue'))
    
    # Classification
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    
    # Relationships
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tickets',
        help_text=_('Business admin who created the ticket')
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        help_text=_('Platform admin assigned to resolve the ticket')
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='support_tickets',
        help_text=_('Tenant associated with this ticket')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional fields
    is_urgent = models.BooleanField(default=False, help_text=_('Mark as urgent for quick response'))
    requires_callback = models.BooleanField(default=False, help_text=_('Business admin requested a callback'))
    callback_phone = models.CharField(max_length=15, blank=True, null=True)
    callback_preferred_time = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = _('Support Ticket')
        verbose_name_plural = _('Support Tickets')
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.ticket_id} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            # Generate ticket ID: ST-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            last_ticket = SupportTicket.objects.filter(
                ticket_id__startswith=f'ST-{today}'
            ).order_by('-ticket_id').first()
            
            if last_ticket:
                last_number = int(last_ticket.ticket_id.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.ticket_id = f'ST-{today}-{new_number:04d}'
        
        # Update timestamps based on status changes
        if self.status == self.Status.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status == self.Status.CLOSED and not self.closed_at:
            self.closed_at = timezone.now()
        
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        return self.status in [self.Status.OPEN, self.Status.IN_PROGRESS, self.Status.REOPENED]

    @property
    def response_time(self):
        """Calculate time from creation to first platform admin response"""
        first_response = self.messages.filter(
            sender__role='platform_admin'
        ).order_by('created_at').first()
        
        if first_response:
            return first_response.created_at - self.created_at
        return None


class TicketMessage(models.Model):
    """
    Messages exchanged between business admin and platform admin for a support ticket.
    """
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text=_('Support ticket this message belongs to')
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_support_messages',
        help_text=_('User who sent this message')
    )
    content = models.TextField(help_text=_('Message content'))
    is_internal = models.BooleanField(
        default=False,
        help_text=_('Internal note visible only to platform admins')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Message metadata
    is_system_message = models.BooleanField(
        default=False,
        help_text=_('System-generated message (status changes, etc.)')
    )
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('text', _('Text')),
            ('status_update', _('Status Update')),
            ('resolution', _('Resolution')),
            ('reopening', _('Reopening')),
        ],
        default='text'
    )

    class Meta:
        verbose_name = _('Ticket Message')
        verbose_name_plural = _('Ticket Messages')
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} on {self.ticket.ticket_id}"

    @property
    def sender_role_display(self):
        """Get the role of the sender for display purposes"""
        role_mapping = {
            'platform_admin': 'Platform Admin',
            'business_admin': 'Business Admin',
            'manager': 'Manager'
        }
        return role_mapping.get(self.sender.role, self.sender.role.title())


class SupportNotification(models.Model):
    """
    Notifications for support ticket updates.
    """
    class NotificationType(models.TextChoices):
        TICKET_CREATED = 'ticket_created', _('Ticket Created')
        TICKET_UPDATED = 'ticket_updated', _('Ticket Updated')
        MESSAGE_RECEIVED = 'message_received', _('Message Received')
        TICKET_RESOLVED = 'ticket_resolved', _('Ticket Resolved')
        TICKET_CLOSED = 'ticket_closed', _('Ticket Closed')
        TICKET_REOPENED = 'ticket_reopened', _('Ticket Reopened')
        CALLBACK_REQUESTED = 'callback_requested', _('Callback Requested')

    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='support_notifications',
        help_text=_('User who will receive this notification')
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Support Notification')
        verbose_name_plural = _('Support Notifications')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} - {self.recipient.username}"


class SupportSettings(models.Model):
    """
    Support system settings and configurations.
    """
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='support_settings'
    )
    
    # Response time settings
    auto_assign_tickets = models.BooleanField(
        default=True,
        help_text=_('Automatically assign tickets to available platform admins')
    )
    max_response_time_hours = models.PositiveIntegerField(
        default=24,
        help_text=_('Maximum response time in hours for non-critical tickets')
    )
    critical_response_time_hours = models.PositiveIntegerField(
        default=4,
        help_text=_('Maximum response time in hours for critical tickets')
    )
    
    # Notification settings
    email_notifications = models.BooleanField(default=True)
    in_app_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # Business hours
    business_hours_start = models.TimeField(default='09:00')
    business_hours_end = models.TimeField(default='18:00')
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Auto-resolution settings
    auto_close_after_days = models.PositiveIntegerField(
        default=7,
        help_text=_('Automatically close resolved tickets after this many days')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Support Settings')
        verbose_name_plural = _('Support Settings')

    def __str__(self):
        return f"Support Settings for {self.tenant.name}" 