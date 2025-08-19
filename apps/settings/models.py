from django.db import models
from django.conf import settings
from apps.tenants.models import Tenant

class BusinessSetting(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='business_settings')
    key = models.CharField(max_length=64)
    value = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tenant.name}: {self.key}"

class Tag(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64)
    is_active = models.BooleanField(default=True)
    auto_rule = models.TextField(blank=True, null=True, help_text='Auto-tagging rule (optional)')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class NotificationTemplate(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='notification_templates')
    name = models.CharField(max_length=64)
    channel = models.CharField(max_length=16, choices=[('whatsapp', 'WhatsApp'), ('sms', 'SMS'), ('email', 'Email')])
    event = models.CharField(max_length=64, help_text='Event trigger, e.g. birthday, purchase')
    template = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.channel})"

class BrandingSetting(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='branding')
    logo = models.ImageField(upload_to='branding/logos/', blank=True, null=True)
    theme_color = models.CharField(max_length=16, default='#1e40af')
    business_name = models.CharField(max_length=128)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.business_name

class LegalSetting(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='legal')
    privacy_policy = models.TextField(blank=True, null=True)
    refund_policy = models.TextField(blank=True, null=True)
    terms_and_conditions = models.TextField(blank=True, null=True)
    digital_receipt = models.TextField(blank=True, null=True)
    disclaimer = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Legal for {self.tenant.name}" 