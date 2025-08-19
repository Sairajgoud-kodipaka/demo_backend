from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()

class WhatsAppSession(models.Model):
    """WhatsApp session management for multiple team members"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        CONNECTING = 'connecting', _('Connecting')
        ERROR = 'error', _('Error')
        DISCONNECTED = 'disconnected', _('Disconnected')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text=_('Session name for identification'))
    phone_number = models.CharField(max_length=20, unique=True)
    session_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INACTIVE)
    
    # Team assignment
    assigned_team_member = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='whatsapp_sessions'
    )
    
    # Session metadata
    last_activity = models.DateTimeField(auto_now=True)
    messages_sent = models.PositiveIntegerField(default=0)
    messages_received = models.PositiveIntegerField(default=0)
    
    # Configuration
    auto_reply_enabled = models.BooleanField(default=False)
    business_hours_enabled = models.BooleanField(default=False)
    business_hours_start = models.TimeField(null=True, blank=True)
    business_hours_end = models.TimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('WhatsApp Session')
        verbose_name_plural = _('WhatsApp Sessions')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.phone_number}"


class WhatsAppContact(models.Model):
    """Customer contact information and chat history"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        BLOCKED = 'blocked', _('Blocked')
        OPTED_OUT = 'opted_out', _('Opted Out')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    
    # Customer information
    customer_type = models.CharField(max_length=20, choices=[
        ('prospect', _('Prospect')),
        ('customer', _('Customer')),
        ('vip', _('VIP Customer')),
        ('returning', _('Returning Customer')),
    ], default='prospect')
    
    # Preferences and settings
    language = models.CharField(max_length=10, default='en')
    timezone = models.CharField(max_length=50, default='UTC')
    opt_in_date = models.DateTimeField(auto_now_add=True)
    last_interaction = models.DateTimeField(auto_now=True)
    
    # Statistics
    total_messages = models.PositiveIntegerField(default=0)
    total_orders = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Tags for segmentation
    tags = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('WhatsApp Contact')
        verbose_name_plural = _('WhatsApp Contacts')
        ordering = ['-last_interaction']
    
    def __str__(self):
        return f"{self.name or 'Unknown'} - {self.phone_number}"


class WhatsAppMessage(models.Model):
    """Individual WhatsApp message storage"""
    
    class Direction(models.TextChoices):
        INBOUND = 'inbound', _('Inbound')
        OUTBOUND = 'outbound', _('Outbound')
    
    class Status(models.TextChoices):
        SENT = 'sent', _('Sent')
        DELIVERED = 'delivered', _('Delivered')
        READ = 'read', _('Read')
        FAILED = 'failed', _('Failed')
        PENDING = 'pending', _('Pending')
    
    class Type(models.TextChoices):
        TEXT = 'text', _('Text')
        IMAGE = 'image', _('Image')
        VIDEO = 'video', _('Video')
        AUDIO = 'audio', _('Audio')
        DOCUMENT = 'document', _('Document')
        LOCATION = 'location', _('Location')
        CONTACT = 'contact', _('Contact')
        TEMPLATE = 'template', _('Template')
        INTERACTIVE = 'interactive', _('Interactive')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(WhatsAppSession, on_delete=models.CASCADE, related_name='messages')
    contact = models.ForeignKey(WhatsAppContact, on_delete=models.CASCADE, related_name='messages')
    
    # Message details
    message_id = models.CharField(max_length=100, unique=True)
    direction = models.CharField(max_length=20, choices=Direction.choices)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.TEXT)
    content = models.TextField()
    media_url = models.URLField(blank=True, null=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    is_bot_response = models.BooleanField(default=False)
    bot_trigger = models.CharField(max_length=100, blank=True, null=True)
    campaign_id = models.UUIDField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('WhatsApp Message')
        verbose_name_plural = _('WhatsApp Messages')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.direction} - {self.contact.phone_number} - {self.content[:50]}"


class WhatsAppBot(models.Model):
    """Bot automation configuration"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        TESTING = 'testing', _('Testing')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INACTIVE)
    
    # Bot configuration
    welcome_message = models.TextField(blank=True)
    fallback_message = models.TextField(blank=True)
    max_conversation_turns = models.PositiveIntegerField(default=5)
    
    # Operating hours
    business_hours_only = models.BooleanField(default=True)
    after_hours_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('WhatsApp Bot')
        verbose_name_plural = _('WhatsApp Bots')
    
    def __str__(self):
        return self.name


class WhatsAppBotTrigger(models.Model):
    """Bot trigger keywords and responses"""
    
    class TriggerType(models.TextChoices):
        KEYWORD = 'keyword', _('Keyword')
        EXACT_MATCH = 'exact_match', _('Exact Match')
        REGEX = 'regex', _('Regular Expression')
        INTENT = 'intent', _('Intent Recognition')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.ForeignKey(WhatsAppBot, on_delete=models.CASCADE, related_name='triggers')
    name = models.CharField(max_length=100)
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices, default=TriggerType.KEYWORD)
    
    # Trigger configuration
    trigger_value = models.CharField(max_length=200, help_text=_('Keyword, exact text, or regex pattern'))
    response_message = models.TextField()
    response_type = models.CharField(max_length=20, choices=WhatsAppMessage.Type.choices, default=WhatsAppMessage.Type.TEXT)
    media_url = models.URLField(blank=True, null=True)
    
    # Advanced features
    requires_human_handoff = models.BooleanField(default=False)
    handoff_message = models.TextField(blank=True)
    priority = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(10)])
    
    # Conditions
    is_active = models.BooleanField(default=True)
    min_confidence = models.FloatField(default=0.8, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('WhatsApp Bot Trigger')
        verbose_name_plural = _('WhatsApp Bot Triggers')
        ordering = ['priority', '-created_at']
    
    def __str__(self):
        return f"{self.bot.name} - {self.name}"


class WhatsAppCampaign(models.Model):
    """Marketing campaign management"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        SCHEDULED = 'scheduled', _('Scheduled')
        ACTIVE = 'active', _('Active')
        PAUSED = 'paused', _('Paused')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')
    
    class Type(models.TextChoices):
        BROADCAST = 'broadcast', _('Broadcast')
        TEMPLATE = 'template', _('Template')
        AUTOMATED = 'automated', _('Automated Sequence')
        TRIGGERED = 'triggered', _('Triggered')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    campaign_type = models.CharField(max_length=20, choices=Type.choices, default=Type.BROADCAST)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # Campaign configuration
    message_template = models.TextField()
    target_audience = models.JSONField(default=dict, help_text=_('Segmentation criteria'))
    scheduled_at = models.DateTimeField(null=True, blank=True)
    
    # Statistics
    total_recipients = models.PositiveIntegerField(default=0)
    messages_sent = models.PositiveIntegerField(default=0)
    messages_delivered = models.PositiveIntegerField(default=0)
    messages_read = models.PositiveIntegerField(default=0)
    replies_received = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    delivery_rate = models.FloatField(default=0.0)
    read_rate = models.FloatField(default=0.0)
    reply_rate = models.FloatField(default=0.0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('WhatsApp Campaign')
        verbose_name_plural = _('WhatsApp Campaigns')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class WhatsAppTeamMember(models.Model):
    """Team member management and permissions"""
    
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Administrator')
        MANAGER = 'manager', _('Manager')
        AGENT = 'agent', _('Customer Service Agent')
        SALES = 'sales', _('Sales Representative')
        MARKETING = 'marketing', _('Marketing Specialist')
        VIEWER = 'viewer', _('Viewer Only')
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        SUSPENDED = 'suspended', _('Suspended')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='whatsapp_team_profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AGENT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    
    # Permissions
    can_send_messages = models.BooleanField(default=True)
    can_manage_campaigns = models.BooleanField(default=False)
    can_manage_bots = models.BooleanField(default=False)
    can_manage_team = models.BooleanField(default=False)
    can_view_analytics = models.BooleanField(default=True)
    
    # Performance tracking
    total_messages_sent = models.PositiveIntegerField(default=0)
    total_customers_helped = models.PositiveIntegerField(default=0)
    average_response_time = models.FloatField(default=0.0)  # in minutes
    customer_satisfaction_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    
    # Availability
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    working_hours = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('WhatsApp Team Member')
        verbose_name_plural = _('WhatsApp Team Members')
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"


class WhatsAppConversation(models.Model):
    """Conversation thread management"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        RESOLVED = 'resolved', _('Resolved')
        ESCALATED = 'escalated', _('Escalated')
        CLOSED = 'closed', _('Closed')
    
    class Priority(models.TextChoices):
        LOW = 'low', _('Low')
        MEDIUM = 'medium', _('Medium')
        HIGH = 'high', _('High')
        URGENT = 'urgent', _('Urgent')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(WhatsAppContact, on_delete=models.CASCADE, related_name='conversations')
    session = models.ForeignKey(WhatsAppSession, on_delete=models.CASCADE, related_name='conversations')
    assigned_agent = models.ForeignKey(WhatsAppTeamMember, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_conversations')
    
    # Conversation details
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    subject = models.CharField(max_length=200, blank=True)
    
    # Tracking
    first_message_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)
    resolution_time = models.FloatField(null=True, blank=True, help_text=_('Time to resolve in minutes'))
    
    # Tags and categorization
    tags = models.JSONField(default=list, blank=True)
    category = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('WhatsApp Conversation')
        verbose_name_plural = _('WhatsApp Conversations')
        ordering = ['-last_message_at']
    
    def __str__(self):
        return f"Conversation with {self.contact.name or self.contact.phone_number}"


class WhatsAppAnalytics(models.Model):
    """Analytics and performance tracking"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    
    # Message statistics
    total_messages_sent = models.PositiveIntegerField(default=0)
    total_messages_received = models.PositiveIntegerField(default=0)
    messages_delivered = models.PositiveIntegerField(default=0)
    messages_read = models.PositiveIntegerField(default=0)
    messages_failed = models.PositiveIntegerField(default=0)
    
    # Response metrics
    average_response_time = models.FloatField(default=0.0)
    first_response_time = models.FloatField(default=0.0)
    resolution_time = models.FloatField(default=0.0)
    
    # Customer metrics
    new_contacts = models.PositiveIntegerField(default=0)
    active_conversations = models.PositiveIntegerField(default=0)
    resolved_conversations = models.PositiveIntegerField(default=0)
    
    # Campaign performance
    campaigns_sent = models.PositiveIntegerField(default=0)
    campaign_delivery_rate = models.FloatField(default=0.0)
    campaign_read_rate = models.FloatField(default=0.0)
    
    # Bot performance
    bot_interactions = models.PositiveIntegerField(default=0)
    bot_resolution_rate = models.FloatField(default=0.0)
    human_handoffs = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('WhatsApp Analytics')
        verbose_name_plural = _('WhatsApp Analytics')
        ordering = ['-date']
        unique_together = ['date']
    
    def __str__(self):
        return f"Analytics for {self.date}"
