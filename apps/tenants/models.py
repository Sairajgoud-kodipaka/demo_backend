from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class Tenant(models.Model):
    """
    Tenant model for multi-tenancy support.
    Each tenant represents a separate business/organization.
    """
    name = models.CharField(max_length=100, help_text=_('Name of the business/organization'))
    slug = models.SlugField(max_length=50, unique=True, help_text=_('Unique identifier for the tenant'))
    
    # Business Information
    business_type = models.CharField(max_length=50, blank=True, null=True)
    industry = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # Contact Information
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    google_maps_url = models.URLField(blank=True, null=True, help_text=_('Google Maps location URL'))
    
    # Subscription and Billing
    subscription_plan = models.CharField(
        max_length=20,
        choices=[
            ('basic', _('Basic')),
            ('professional', _('Professional')),
            ('enterprise', _('Enterprise')),
        ],
        default='basic'
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('active', _('Active')),
            ('inactive', _('Inactive')),
            ('suspended', _('Suspended')),
            ('cancelled', _('Cancelled')),
        ],
        default='active'
    )
    
    # Settings
    is_active = models.BooleanField(default=True)
    max_users = models.PositiveIntegerField(default=5)
    max_storage_gb = models.PositiveIntegerField(default=10)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    subscription_start = models.DateTimeField(blank=True, null=True)
    subscription_end = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _('Tenant')
        verbose_name_plural = _('Tenants')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_subscription_active(self):
        """Check if the tenant's subscription is currently active."""
        if self.subscription_status != 'active':
            return False
        if self.subscription_end and self.subscription_end < timezone.now():
            return False
        return True

    @property
    def user_count(self):
        """Get the current number of users for this tenant."""
        return self.users.count()

    def can_add_user(self):
        """Check if the tenant can add more users based on their plan."""
        return self.user_count < self.max_users
