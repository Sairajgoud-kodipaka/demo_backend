from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.users.models import User
from apps.clients.models import Client


class Escalation(models.Model):
    """
    Model for escalating customer issues to managers.
    """
    class Priority(models.TextChoices):
        LOW = 'low', _('Low')
        MEDIUM = 'medium', _('Medium')
        HIGH = 'high', _('High')
        URGENT = 'urgent', _('Urgent')

    class Status(models.TextChoices):
        OPEN = 'open', _('Open')
        IN_PROGRESS = 'in_progress', _('In Progress')
        PENDING_CUSTOMER = 'pending_customer', _('Pending Customer Response')
        RESOLVED = 'resolved', _('Resolved')
        CLOSED = 'closed', _('Closed')
        CANCELLED = 'cancelled', _('Cancelled')

    class Category(models.TextChoices):
        PRODUCT_ISSUE = 'product_issue', _('Product Issue')
        SERVICE_QUALITY = 'service_quality', _('Service Quality')
        BILLING = 'billing', _('Billing')
        DELIVERY = 'delivery', _('Delivery')
        TECHNICAL = 'technical', _('Technical')
        COMPLAINT = 'complaint', _('Complaint')
        REFUND = 'refund', _('Refund')
        OTHER = 'other', _('Other')

    # Basic Information
    title = models.CharField(max_length=200, help_text=_('Brief description of the issue'))
    description = models.TextField(help_text=_('Detailed description of the issue'))
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
        help_text=_('Category of the escalation')
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text=_('Priority level of the escalation')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        help_text=_('Current status of the escalation')
    )

    # Relationships
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='escalations',
        help_text=_('Client who raised the issue')
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_escalations',
        help_text=_('User who created the escalation')
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_escalations',
        help_text=_('Manager assigned to handle the escalation')
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='escalations',
        help_text=_('Tenant this escalation belongs to')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # SLA Tracking
    sla_hours = models.PositiveIntegerField(
        default=24,
        help_text=_('SLA hours for resolution')
    )
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Due date based on SLA')
    )

    class Meta:
        verbose_name = _('Escalation')
        verbose_name_plural = _('Escalations')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.client.full_name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Set due date based on SLA when escalation is created
        if not self.pk and not self.due_date:
            self.due_date = timezone.now() + timezone.timedelta(hours=self.sla_hours)
        
        # Update timestamps when status changes
        if self.pk:
            old_instance = Escalation.objects.get(pk=self.pk)
            if old_instance.status != self.status:
                if self.status == self.Status.IN_PROGRESS and not self.assigned_at:
                    self.assigned_at = timezone.now()
                elif self.status == self.Status.RESOLVED and not self.resolved_at:
                    self.resolved_at = timezone.now()
                elif self.status == self.Status.CLOSED and not self.closed_at:
                    self.closed_at = timezone.now()
        
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if the escalation is overdue based on SLA."""
        if self.due_date and self.status not in [self.Status.RESOLVED, self.Status.CLOSED]:
            return timezone.now() > self.due_date
        return False

    @property
    def time_to_resolution(self):
        """Calculate time to resolution in hours."""
        if self.resolved_at and self.created_at:
            return (self.resolved_at - self.created_at).total_seconds() / 3600
        return None

    @property
    def sla_compliance(self):
        """Check if SLA was met."""
        if self.time_to_resolution is not None:
            return self.time_to_resolution <= self.sla_hours
        return None


class EscalationNote(models.Model):
    """
    Model for tracking notes and updates on escalations.
    """
    escalation = models.ForeignKey(
        Escalation,
        on_delete=models.CASCADE,
        related_name='notes',
        help_text=_('Escalation this note belongs to')
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='escalation_notes',
        help_text=_('User who wrote the note')
    )
    content = models.TextField(help_text=_('Note content'))
    is_internal = models.BooleanField(
        default=False,
        help_text=_('Whether this note is internal (not visible to customer)')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Escalation Note')
        verbose_name_plural = _('Escalation Notes')
        ordering = ['-created_at']

    def __str__(self):
        return f"Note by {self.author.username} on {self.escalation.title}"


class EscalationTemplate(models.Model):
    """
    Model for predefined escalation response templates.
    """
    name = models.CharField(max_length=100, help_text=_('Template name'))
    category = models.CharField(
        max_length=20,
        choices=Escalation.Category.choices,
        help_text=_('Category this template applies to')
    )
    subject = models.CharField(max_length=200, help_text=_('Email subject line'))
    content = models.TextField(help_text=_('Template content'))
    is_active = models.BooleanField(default=True)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='escalation_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Escalation Template')
        verbose_name_plural = _('Escalation Templates')
        ordering = ['name']

    def __str__(self):
        return self.name
