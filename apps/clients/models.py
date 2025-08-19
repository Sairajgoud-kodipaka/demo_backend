from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
import json
import datetime
from decimal import Decimal


def serialize_field(value):
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, 'pk'):
        return value.pk
    return value


class CustomerTag(models.Model):
    """
    Tag model for customer segmentation, supporting all tag categories (intent, product, revenue, demographic, source, status, community, event).
    """
    CATEGORY_CHOICES = [
        ("intent", "Purchase Intent/Visit Reason"),
        ("product", "Product Interest"),
        ("revenue", "Revenue-Based"),
        ("demographic", "Demographic/Age"),
        ("source", "Lead Source"),
        ("status", "CRM Status"),
        ("community", "Community/Relationship"),
        ("event", "Event-Driven"),
        ("custom", "Custom"),
    ]
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="custom")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer Tag"
        verbose_name_plural = "Customer Tags"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.category})"


class Client(models.Model):
    """
    Client/Customer model for CRM.
    """
    class Status(models.TextChoices):
        LEAD = 'lead', _('Lead')
        PROSPECT = 'prospect', _('Prospect')
        CUSTOMER = 'customer', _('Customer')
        INACTIVE = 'inactive', _('Inactive')

    class Source(models.TextChoices):
        WEBSITE = 'website', _('Website')
        REFERRAL = 'referral', _('Referral')
        SOCIAL_MEDIA = 'social_media', _('Social Media')
        ADVERTISING = 'advertising', _('Advertising')
        COLD_CALL = 'cold_call', _('Cold Call')
        OTHER = 'other', _('Other')

    # Basic Information
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True, null=True)
    customer_type = models.CharField(max_length=30, default='individual')

    # Address
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)

    # Personal Information
    date_of_birth = models.DateField(blank=True, null=True)
    anniversary_date = models.DateField(blank=True, null=True)

    # Jewelry Preferences
    preferred_metal = models.CharField(max_length=30, blank=True, null=True)
    preferred_stone = models.CharField(max_length=30, blank=True, null=True)
    ring_size = models.CharField(max_length=10, blank=True, null=True)
    budget_range = models.CharField(max_length=30, blank=True, null=True)

    # Lead Information
    lead_source = models.CharField(max_length=50, blank=True, null=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_clients')
    
    # Status field
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.LEAD
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Demographics & Visit
    community = models.CharField(max_length=50, blank=True, null=True)
    mother_tongue = models.CharField(max_length=50, blank=True, null=True)
    reason_for_visit = models.CharField(max_length=100, blank=True, null=True)
    age_of_end_user = models.CharField(max_length=30, blank=True, null=True)
    saving_scheme = models.CharField(max_length=30, blank=True, null=True)
    catchment_area = models.CharField(max_length=100, blank=True, null=True)
    
    # Follow-up & Summary
    next_follow_up = models.CharField(max_length=255, blank=True, null=True)
    summary_notes = models.TextField(blank=True, null=True, default='')

    # Customer Interests (as JSON)
    customer_interests = models.JSONField(default=list, blank=True)

    # Tenant relationship
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='clients', null=True, blank=True)
    
    # Store relationship - Direct link to store for store-based visibility
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='clients', null=True, blank=True, help_text=_('Store this customer belongs to'))

    # Tags relationship
    tags = models.ManyToManyField('CustomerTag', related_name='clients', blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Soft delete fields
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')
        ordering = ['-created_at']
        unique_together = ['email', 'tenant']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_lead(self):
        return self.status == self.Status.LEAD

    @property
    def is_customer(self):
        return self.status == self.Status.CUSTOMER

    def update_lead_score(self, points):
        """Update the lead score by adding points."""
        self.lead_score = min(100, max(0, self.lead_score + points))
        self.save()

    def mark_as_contacted(self):
        """Mark the client as contacted and update the last contact date."""
        from django.utils import timezone
        self.last_contact_date = timezone.now()
        self.save()


class ClientInteraction(models.Model):
    """
    Model to track interactions with clients.
    """
    class InteractionType(models.TextChoices):
        CALL = 'call', _('Phone Call')
        EMAIL = 'email', _('Email')
        MEETING = 'meeting', _('Meeting')
        WHATSAPP = 'whatsapp', _('WhatsApp')
        VISIT = 'visit', _('Store Visit')
        OTHER = 'other', _('Other')

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='interactions'
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=InteractionType.choices
    )
    subject = models.CharField(max_length=200)
    description = models.TextField()
    
    # Outcome
    outcome = models.CharField(
        max_length=20,
        choices=[
            ('positive', _('Positive')),
            ('neutral', _('Neutral')),
            ('negative', _('Negative')),
        ],
        default='neutral'
    )
    
    # Follow-up
    requires_follow_up = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(blank=True, null=True)
    follow_up_notes = models.TextField(blank=True, null=True)
    
    # User who made the interaction
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='client_interactions'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Client Interaction')
        verbose_name_plural = _('Client Interactions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client.full_name} - {self.interaction_type} - {self.subject}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', _('Scheduled')
        CONFIRMED = 'confirmed', _('Confirmed')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')
        RESCHEDULED = 'rescheduled', _('Rescheduled')
        NO_SHOW = 'no_show', _('No Show')

    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='appointments')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='appointments')
    date = models.DateField()
    time = models.TimeField()
    purpose = models.CharField(max_length=255)
    notes = models.TextField(blank=True, null=True)
    
    # Status and lifecycle
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    
    # Reminder settings
    reminder_sent = models.BooleanField(default=False)
    reminder_date = models.DateTimeField(blank=True, null=True)
    
    # Follow-up settings
    requires_follow_up = models.BooleanField(default=False)
    follow_up_date = models.DateField(blank=True, null=True)
    follow_up_notes = models.TextField(blank=True, null=True)
    
    # Duration (in minutes)
    duration = models.PositiveIntegerField(default=60, help_text=_('Duration in minutes'))
    
    # Location/venue
    location = models.CharField(max_length=255, blank=True, null=True)
    
    # Outcome tracking
    outcome_notes = models.TextField(blank=True, null=True)
    next_action = models.CharField(max_length=255, blank=True, null=True)
    
    # User tracking
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_appointments'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Appointment')
        verbose_name_plural = _('Appointments')
        ordering = ['-date', '-time']

    def __str__(self):
        return f"{self.client.full_name} - {self.date} {self.time} ({self.get_status_display()})"

    @property
    def is_upcoming(self):
        """Check if appointment is in the future"""
        from django.utils import timezone
        now = timezone.now()
        appointment_datetime = timezone.make_aware(
            timezone.datetime.combine(self.date, self.time)
        )
        return appointment_datetime > now

    @property
    def is_today(self):
        """Check if appointment is today"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.date == today

    @property
    def is_overdue(self):
        """Check if appointment is overdue"""
        from django.utils import timezone
        now = timezone.now()
        appointment_datetime = timezone.make_aware(
            timezone.datetime.combine(self.date, self.time)
        )
        return appointment_datetime < now and self.status == self.Status.SCHEDULED

    def send_reminder(self):
        """Send reminder for this appointment"""
        # TODO: Implement actual reminder sending logic
        self.reminder_sent = True
        self.save(update_fields=['reminder_sent'])

    def mark_completed(self, outcome_notes=None):
        """Mark appointment as completed"""
        self.status = self.Status.COMPLETED
        if outcome_notes:
            self.outcome_notes = outcome_notes
        self.save()

    def cancel_appointment(self, reason=None):
        """Cancel the appointment"""
        self.status = self.Status.CANCELLED
        if reason:
            self.notes = f"{self.notes or ''}\n\nCancellation reason: {reason}"
        self.save()

    def reschedule_appointment(self, new_date, new_time, reason=None):
        """Reschedule the appointment"""
        self.status = self.Status.RESCHEDULED
        if reason:
            self.notes = f"{self.notes or ''}\n\nReschedule reason: {reason}"
        # Create a new appointment with the new date/time
        new_appointment = Appointment.objects.create(
            client=self.client,
            tenant=self.tenant,
            date=new_date,
            time=new_time,
            purpose=self.purpose,
            notes=self.notes,
            status=self.Status.SCHEDULED,
            duration=self.duration,
            location=self.location,
            assigned_to=self.assigned_to,
            created_by=self.created_by
        )
        return new_appointment


class FollowUp(models.Model):
    """
    Model to track follow-ups for appointments and client interactions.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')

    class Type(models.TextChoices):
        APPOINTMENT = 'appointment', _('Appointment Follow-up')
        INTERACTION = 'interaction', _('Interaction Follow-up')
        GENERAL = 'general', _('General Follow-up')

    # Relationships
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='follow_ups')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='follow_ups')
    appointment = models.ForeignKey(
        'Appointment', 
        on_delete=models.CASCADE, 
        related_name='follow_ups', 
        null=True, 
        blank=True
    )
    interaction = models.ForeignKey(
        'ClientInteraction', 
        on_delete=models.CASCADE, 
        related_name='follow_ups', 
        null=True, 
        blank=True
    )
    
    # Follow-up details
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.GENERAL)
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateField()
    due_time = models.TimeField(blank=True, null=True)
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('urgent', _('Urgent')),
        ],
        default='medium'
    )
    
    # Reminder settings
    reminder_sent = models.BooleanField(default=False)
    reminder_date = models.DateTimeField(blank=True, null=True)
    
    # Outcome
    outcome_notes = models.TextField(blank=True, null=True)
    next_action = models.CharField(max_length=255, blank=True, null=True)
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_follow_ups'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_follow_ups'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Follow-up')
        verbose_name_plural = _('Follow-ups')
        ordering = ['-due_date', '-due_time']

    def __str__(self):
        return f"{self.title} - {self.client.full_name} ({self.get_status_display()})"

    @property
    def is_overdue(self):
        """Check if follow-up is overdue"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.due_date < today and self.status == self.Status.PENDING

    @property
    def is_due_today(self):
        """Check if follow-up is due today"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.due_date == today

    def mark_completed(self, outcome_notes=None):
        """Mark follow-up as completed"""
        from django.utils import timezone
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        if outcome_notes:
            self.outcome_notes = outcome_notes
        self.save()

    def send_reminder(self):
        """Send reminder for this follow-up"""
        # TODO: Implement actual reminder sending logic
        self.reminder_sent = True
        self.save(update_fields=['reminder_sent'])


class Task(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='tasks')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, default='pending')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.client.full_name}"

class Announcement(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Purchase(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='purchases')
    product_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purchase_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.client.full_name} - {self.product_name} - {self.amount}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('restore', 'Restore'),
    ]
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_action_display()} by {self.user} on {self.timestamp}"


@receiver(pre_save, sender=Client)
def log_client_update(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = Client.objects.get(pk=instance.pk)
            before = {field.name: serialize_field(getattr(old, field.name)) for field in instance._meta.fields}
        except Client.DoesNotExist:
            before = None
        instance._auditlog_before = before
    else:
        instance._auditlog_before = None

@receiver(post_save, sender=Client)
def create_audit_log_on_save(sender, instance, created, **kwargs):
    from .models import AuditLog
    user = getattr(instance, '_auditlog_user', None)
    before = getattr(instance, '_auditlog_before', None)
    after = {field.name: serialize_field(getattr(instance, field.name)) for field in instance._meta.fields}
    action = 'create' if created else 'update'
    if before != after:
        AuditLog.objects.create(
            client=instance,
            action=action,
            user=user,
            before=before,
            after=after
        )

@receiver(pre_delete, sender=Client)
def create_audit_log_on_delete(sender, instance, **kwargs):
    from .models import AuditLog
    user = getattr(instance, '_auditlog_user', None)
    before = {field.name: serialize_field(getattr(instance, field.name)) for field in instance._meta.fields}
    AuditLog.objects.create(
        client=instance,
        action='delete',
        user=user,
        before=before,
        after=None
    )
