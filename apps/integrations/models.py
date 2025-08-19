from django.db import models
from django.utils.translation import gettext_lazy as _


class Integration(models.Model):
    """
    Base integration model for third-party platform connections.
    """
    class Platform(models.TextChoices):
        WHATSAPP = 'whatsapp', _('WhatsApp Business')
        DUKAAN = 'dukaan', _('Dukaan')
        QUICKSELL = 'quicksell', _('QuickSell')
        SHOPIFY = 'shopify', _('Shopify')
        WOOCOMMERCE = 'woocommerce', _('WooCommerce')
        PAYMENT_GATEWAY = 'payment_gateway', _('Payment Gateway')

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        ERROR = 'error', _('Error')
        PENDING = 'pending', _('Pending')

    # Integration Information
    platform = models.CharField(max_length=20, choices=Platform.choices)
    name = models.CharField(max_length=100, help_text=_('Custom name for this integration'))
    
    # Configuration
    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    webhook_url = models.URLField(blank=True, null=True)
    config_data = models.JSONField(default=dict, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INACTIVE
    )
    is_enabled = models.BooleanField(default=False)
    
    # Error tracking
    last_error = models.TextField(blank=True, null=True)
    last_sync = models.DateTimeField(blank=True, null=True)
    
    # Tenant relationship
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='integrations'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Integration')
        verbose_name_plural = _('Integrations')
        unique_together = ['platform', 'tenant']

    def __str__(self):
        return f"{self.get_platform_display()} - {self.name}"

    @property
    def is_whatsapp(self):
        return self.platform == self.Platform.WHATSAPP

    @property
    def is_ecommerce(self):
        return self.platform in [self.Platform.DUKAAN, self.Platform.QUICKSELL, self.Platform.SHOPIFY, self.Platform.WOOCOMMERCE]


class WhatsAppIntegration(models.Model):
    """
    WhatsApp Business API integration details.
    """
    integration = models.OneToOneField(
        Integration,
        on_delete=models.CASCADE,
        related_name='whatsapp_config'
    )
    
    # WhatsApp Business API Configuration
    phone_number = models.CharField(max_length=20, help_text=_('WhatsApp Business phone number'))
    business_name = models.CharField(max_length=100, blank=True, null=True)
    business_description = models.TextField(blank=True, null=True)
    
    # Message Templates
    welcome_message = models.TextField(blank=True, null=True)
    order_confirmation_template = models.CharField(max_length=100, blank=True, null=True)
    order_status_template = models.CharField(max_length=100, blank=True, null=True)
    
    # Settings
    auto_reply_enabled = models.BooleanField(default=False)
    order_notifications_enabled = models.BooleanField(default=True)
    marketing_messages_enabled = models.BooleanField(default=False)
    
    # Statistics
    messages_sent = models.PositiveIntegerField(default=0)
    messages_received = models.PositiveIntegerField(default=0)
    last_message_sent = models.DateTimeField(blank=True, null=True)
    last_message_received = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _('WhatsApp Integration')
        verbose_name_plural = _('WhatsApp Integrations')

    def __str__(self):
        return f"WhatsApp - {self.phone_number}"


class EcommerceIntegration(models.Model):
    """
    E-commerce platform integration details.
    """
    integration = models.OneToOneField(
        Integration,
        on_delete=models.CASCADE,
        related_name='ecommerce_config'
    )
    
    # Platform Configuration
    store_url = models.URLField(blank=True, null=True)
    store_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Sync Settings
    sync_products = models.BooleanField(default=True)
    sync_orders = models.BooleanField(default=True)
    sync_customers = models.BooleanField(default=True)
    sync_inventory = models.BooleanField(default=True)
    
    # Sync Frequency
    sync_interval_hours = models.PositiveIntegerField(default=24)
    last_product_sync = models.DateTimeField(blank=True, null=True)
    last_order_sync = models.DateTimeField(blank=True, null=True)
    last_customer_sync = models.DateTimeField(blank=True, null=True)
    
    # Statistics
    products_synced = models.PositiveIntegerField(default=0)
    orders_synced = models.PositiveIntegerField(default=0)
    customers_synced = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _('E-commerce Integration')
        verbose_name_plural = _('E-commerce Integrations')

    def __str__(self):
        return f"{self.integration.get_platform_display()} - {self.store_name}"


class IntegrationLog(models.Model):
    """
    Log for tracking integration activities and errors.
    """
    class LogLevel(models.TextChoices):
        INFO = 'info', _('Info')
        WARNING = 'warning', _('Warning')
        ERROR = 'error', _('Error')
        SUCCESS = 'success', _('Success')

    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    level = models.CharField(max_length=10, choices=LogLevel.choices, default=LogLevel.INFO)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Integration Log')
        verbose_name_plural = _('Integration Logs')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.integration.name} - {self.level} - {self.message[:50]}"
