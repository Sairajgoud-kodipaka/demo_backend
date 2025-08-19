from django.db import models
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant
from apps.stores.models import Store

User = get_user_model()


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('appointment_reminder', 'Appointment Reminder'),
        ('order_status', 'Order Status'),
        ('inventory_alert', 'Inventory Alert'),
        ('new_customer', 'New Customer'),
        ('deal_update', 'Deal Update'),
        ('payment_received', 'Payment Received'),
        ('task_reminder', 'Task Reminder'),
        ('announcement', 'Announcement'),
        ('escalation', 'Escalation'),
        ('marketing_campaign', 'Marketing Campaign'),
        ('stock_transfer_request', 'Stock Transfer Request'),
        ('stock_transfer_approved', 'Stock Transfer Approved'),
        ('stock_transfer_completed', 'Stock Transfer Completed'),
        ('stock_transfer_cancelled', 'Stock Transfer Cancelled'),
        ('stock_transfer_rejected', 'Stock Transfer Rejected'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('unread', 'Unread'),
        ('read', 'Read'),
    ]
    
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unread')
    
    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_notifications')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='tenant_notifications')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, related_name='store_notifications')
    
    # Action details
    action_url = models.CharField(max_length=255, blank=True, null=True)
    action_text = models.CharField(max_length=100, blank=True, null=True)
    is_persistent = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['store', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        from django.utils import timezone
        self.status = 'read'
        self.read_at = timezone.now()
        self.save()


class NotificationSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_notification_settings')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='tenant_notification_settings')
    
    # Email notifications
    email_enabled = models.BooleanField(default=True)
    email_types = models.JSONField(default=list)
    email_frequency = models.CharField(max_length=20, default='immediate')
    
    # Push notifications
    push_enabled = models.BooleanField(default=True)
    push_types = models.JSONField(default=list)
    
    # In-app notifications
    in_app_enabled = models.BooleanField(default=True)
    in_app_types = models.JSONField(default=list)
    in_app_sound = models.BooleanField(default=True)
    in_app_desktop = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    quiet_hours_timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    
    # Preferences
    appointment_reminders = models.BooleanField(default=True)
    deal_updates = models.BooleanField(default=True)
    order_notifications = models.BooleanField(default=True)
    inventory_alerts = models.BooleanField(default=True)
    task_reminders = models.BooleanField(default=True)
    announcements = models.BooleanField(default=True)
    escalations = models.BooleanField(default=True)
    marketing_updates = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Notification Settings'
    
    def __str__(self):
        return f"Settings for {self.user.username}" 