from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()

class MarketingCampaign(models.Model):
    """
    Marketing campaign model for managing various types of campaigns
    """
    class CampaignType(models.TextChoices):
        WHATSAPP = 'whatsapp', _('WhatsApp')
        EMAIL = 'email', _('Email')
        SMS = 'sms', _('SMS')
        SOCIAL_MEDIA = 'social_media', _('Social Media')
        ECOMMERCE = 'ecommerce', _('E-commerce')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        SCHEDULED = 'scheduled', _('Scheduled')
        ACTIVE = 'active', _('Active')
        PAUSED = 'paused', _('Paused')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')

    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text=_('Campaign name'))
    description = models.TextField(blank=True, null=True)
    campaign_type = models.CharField(max_length=20, choices=CampaignType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # Targeting
    target_audience = models.JSONField(default=list, help_text=_('List of customer segments to target'))
    estimated_reach = models.PositiveIntegerField(default=0, help_text=_('Estimated number of recipients'))
    
    # Content
    message_template = models.ForeignKey('MessageTemplate', on_delete=models.SET_NULL, null=True, blank=True)
    custom_message = models.TextField(blank=True, null=True)
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Performance Tracking
    messages_sent = models.PositiveIntegerField(default=0)
    messages_delivered = models.PositiveIntegerField(default=0)
    messages_read = models.PositiveIntegerField(default=0)
    replies_received = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    revenue_generated = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Relationships
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_campaigns')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='marketing_campaigns')
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='marketing_campaigns', null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Marketing Campaign')
        verbose_name_plural = _('Marketing Campaigns')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_campaign_type_display()})"

    @property
    def delivery_rate(self):
        """Calculate delivery rate percentage"""
        if self.messages_sent > 0:
            return (self.messages_delivered / self.messages_sent) * 100
        return 0

    @property
    def read_rate(self):
        """Calculate read rate percentage"""
        if self.messages_delivered > 0:
            return (self.messages_read / self.messages_delivered) * 100
        return 0

    @property
    def reply_rate(self):
        """Calculate reply rate percentage"""
        if self.messages_read > 0:
            return (self.replies_received / self.messages_read) * 100
        return 0

    @property
    def conversion_rate(self):
        """Calculate conversion rate percentage"""
        if self.messages_sent > 0:
            return (self.conversions / self.messages_sent) * 100
        return 0

    @property
    def roi(self):
        """Calculate ROI if cost is available"""
        # This would need cost tracking to be implemented
        return 0


class MessageTemplate(models.Model):
    """
    Reusable message templates for campaigns
    """
    class TemplateType(models.TextChoices):
        WHATSAPP = 'whatsapp', _('WhatsApp')
        EMAIL = 'email', _('Email')
        SMS = 'sms', _('SMS')
        SOCIAL_MEDIA = 'social_media', _('Social Media')

    class Category(models.TextChoices):
        PROMOTIONAL = 'promotional', _('Promotional')
        TRANSACTIONAL = 'transactional', _('Transactional')
        INFORMATIONAL = 'informational', _('Informational')
        GREETING = 'greeting', _('Greeting')
        FOLLOW_UP = 'follow_up', _('Follow-up')

    # Basic Information
    name = models.CharField(max_length=200, help_text=_('Template name'))
    template_type = models.CharField(max_length=20, choices=TemplateType.choices)
    category = models.CharField(max_length=20, choices=Category.choices)
    
    # Content
    subject = models.CharField(max_length=200, blank=True, null=True, help_text=_('Email subject line'))
    message_content = models.TextField(help_text=_('Message content with variables like {{customer_name}}'))
    
    # Variables
    variables = models.JSONField(default=list, help_text=_('List of available variables for this template'))
    
    # Approval Status (for WhatsApp Business API)
    is_approved = models.BooleanField(default=False, help_text=_('Whether template is approved by WhatsApp'))
    approval_status = models.CharField(max_length=20, default='pending', help_text=_('WhatsApp approval status'))
    
    # Usage Tracking
    usage_count = models.PositiveIntegerField(default=0, help_text=_('Number of times this template has been used'))
    
    # Relationships
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_templates')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='message_templates')
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='message_templates', null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Message Template')
        verbose_name_plural = _('Message Templates')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class EcommercePlatform(models.Model):
    """
    E-commerce platform integration model
    """
    class PlatformType(models.TextChoices):
        DUKAAN = 'dukaan', _('Dukaan')
        QUICKSELL = 'quicksell', _('QuickSell')
        SHOPIFY = 'shopify', _('Shopify')
        WOOCOMMERCE = 'woocommerce', _('WooCommerce')
        CUSTOM = 'custom', _('Custom')

    class Status(models.TextChoices):
        CONNECTED = 'connected', _('Connected')
        DISCONNECTED = 'disconnected', _('Disconnected')
        ERROR = 'error', _('Error')

    # Basic Information
    name = models.CharField(max_length=100, help_text=_('Platform name'))
    platform_type = models.CharField(max_length=20, choices=PlatformType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DISCONNECTED)
    
    # Connection Details
    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    webhook_url = models.URLField(blank=True, null=True)
    store_url = models.URLField(blank=True, null=True)
    
    # Sync Information
    last_sync = models.DateTimeField(null=True, blank=True)
    sync_frequency = models.PositiveIntegerField(default=3600, help_text=_('Sync frequency in seconds'))
    
    # Statistics
    total_products = models.PositiveIntegerField(default=0)
    total_orders = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Relationships
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='ecommerce_platforms')
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='ecommerce_platforms', null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('E-commerce Platform')
        verbose_name_plural = _('E-commerce Platforms')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_platform_type_display()})"


class MarketingAnalytics(models.Model):
    """
    Marketing analytics and performance tracking
    """
    # Campaign Performance
    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name='analytics')
    
    # Metrics
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Audience Demographics
    age_groups = models.JSONField(default=dict, help_text=_('Age group distribution'))
    gender_distribution = models.JSONField(default=dict, help_text=_('Gender distribution'))
    device_types = models.JSONField(default=dict, help_text=_('Device type distribution'))
    locations = models.JSONField(default=dict, help_text=_('Geographic distribution'))
    
    # Time-based Data
    date = models.DateField()
    hour = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(23)])
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Marketing Analytics')
        verbose_name_plural = _('Marketing Analytics')
        ordering = ['-date', '-hour']
        unique_together = ['campaign', 'date', 'hour']

    def __str__(self):
        return f"{self.campaign.name} - {self.date}"


class CustomerSegment(models.Model):
    """
    Customer segmentation for targeted marketing
    """
    name = models.CharField(max_length=200, help_text=_('Segment name'))
    description = models.TextField(blank=True, null=True)
    
    # Segment Criteria
    criteria = models.JSONField(default=dict, help_text=_('Segment criteria (age, location, purchase history, etc.)'))
    
    # Statistics
    customer_count = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Performance
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text=_('Conversion rate percentage'))
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text=_('Engagement rate percentage'))
    
    # Relationships
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_segments')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='customer_segments')
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='customer_segments', null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Customer Segment')
        verbose_name_plural = _('Customer Segments')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.customer_count} customers)"


class MarketingEvent(models.Model):
    """
    Marketing events and activities tracking
    """
    class EventType(models.TextChoices):
        CAMPAIGN_LAUNCHED = 'campaign_launched', _('Campaign Launched')
        CAMPAIGN_COMPLETED = 'campaign_completed', _('Campaign Completed')
        TEMPLATE_CREATED = 'template_created', _('Template Created')
        TEMPLATE_APPROVED = 'template_approved', _('Template Approved')
        PLATFORM_CONNECTED = 'platform_connected', _('Platform Connected')
        SEGMENT_CREATED = 'segment_created', _('Segment Created')
        HIGH_CONVERSION = 'high_conversion', _('High Conversion')
        LOW_PERFORMANCE = 'low_performance', _('Low Performance')

    # Event Information
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Related Objects
    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, null=True, blank=True)
    template = models.ForeignKey(MessageTemplate, on_delete=models.CASCADE, null=True, blank=True)
    platform = models.ForeignKey(EcommercePlatform, on_delete=models.CASCADE, null=True, blank=True)
    segment = models.ForeignKey(CustomerSegment, on_delete=models.CASCADE, null=True, blank=True)
    
    # Event Data
    event_data = models.JSONField(default=dict, help_text=_('Additional event data'))
    
    # Relationships
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='marketing_events')
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='marketing_events', null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Marketing Event')
        verbose_name_plural = _('Marketing Events')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_event_type_display()}: {self.title}"
