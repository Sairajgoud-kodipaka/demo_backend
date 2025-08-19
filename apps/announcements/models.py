from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

User = get_user_model()


class Announcement(models.Model):
    """
    Announcement model for system-wide and team-specific communications.
    """
    class AnnouncementType(models.TextChoices):
        SYSTEM_WIDE = 'system_wide', _('System-wide')
        TEAM_SPECIFIC = 'team_specific', _('Team-specific')
        STORE_SPECIFIC = 'store_specific', _('Store-specific')
        ROLE_SPECIFIC = 'role_specific', _('Role-specific')

    class Priority(models.TextChoices):
        LOW = 'low', _('Low')
        MEDIUM = 'medium', _('Medium')
        HIGH = 'high', _('High')
        URGENT = 'urgent', _('Urgent')

    # Basic information
    title = models.CharField(max_length=200, help_text=_('Announcement title'))
    content = models.TextField(help_text=_('Announcement content'))
    announcement_type = models.CharField(
        max_length=20,
        choices=AnnouncementType.choices,
        default=AnnouncementType.SYSTEM_WIDE,
        help_text=_('Type of announcement')
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text=_('Priority level of the announcement')
    )

    # Targeting
    target_roles = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of user roles to target (e.g., ["manager", "inhouse_sales"])')
    )
    target_stores = models.ManyToManyField(
        'stores.Store',
        blank=True,
        related_name='announcements',
        help_text=_('Stores to target (leave empty for all stores)')
    )
    target_tenants = models.ManyToManyField(
        'tenants.Tenant',
        blank=True,
        related_name='targeted_announcements',
        help_text=_('Tenants to target (leave empty for all tenants)')
    )

    # Visibility and pinning
    is_pinned = models.BooleanField(
        default=False,
        help_text=_('Whether this announcement is pinned to the top')
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether this announcement is currently active')
    )
    requires_acknowledgment = models.BooleanField(
        default=False,
        help_text=_('Whether users must acknowledge this announcement')
    )

    # Scheduling
    publish_at = models.DateTimeField(
        default=timezone.now,
        help_text=_('When to publish this announcement')
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When this announcement expires (null for no expiration)')
    )

    # Author and metadata
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_announcements',
        help_text=_('User who created this announcement')
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='system_announcements',
        help_text=_('Tenant this announcement belongs to')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Announcement')
        verbose_name_plural = _('Announcements')
        ordering = ['-is_pinned', '-priority', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_announcement_type_display()})"

    @property
    def is_expired(self):
        """Check if the announcement has expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_published(self):
        """Check if the announcement is currently published."""
        return self.is_active and not self.is_expired and timezone.now() >= self.publish_at

    def get_priority_color(self):
        """Get the color class for the priority level."""
        colors = {
            'low': 'text-gray-500',
            'medium': 'text-blue-600',
            'high': 'text-orange-600',
            'urgent': 'text-red-600'
        }
        return colors.get(self.priority, 'text-gray-600')


class AnnouncementRead(models.Model):
    """
    Track which users have read which announcements.
    """
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='reads',
        help_text=_('Announcement that was read')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='announcement_reads',
        help_text=_('User who read the announcement')
    )
    read_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(
        default=False,
        help_text=_('Whether the user acknowledged the announcement')
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Announcement Read')
        verbose_name_plural = _('Announcement Reads')
        unique_together = ['announcement', 'user']
        ordering = ['-read_at']

    def __str__(self):
        return f"{self.user.username} read {self.announcement.title}"

    def save(self, *args, **kwargs):
        if self.acknowledged and not self.acknowledged_at:
            self.acknowledged_at = timezone.now()
        super().save(*args, **kwargs)


class TeamMessage(models.Model):
    """
    Team messaging and collaboration model.
    """
    class MessageType(models.TextChoices):
        GENERAL = 'general', _('General')
        TASK = 'task', _('Task-related')
        CUSTOMER = 'customer', _('Customer-related')
        URGENT = 'urgent', _('Urgent')

    # Message content
    subject = models.CharField(max_length=200, help_text=_('Message subject'))
    content = models.TextField(help_text=_('Message content'))
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.GENERAL,
        help_text=_('Type of message')
    )

    # Targeting
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        help_text=_('User who sent the message')
    )
    recipients = models.ManyToManyField(
        User,
        related_name='received_messages',
        help_text=_('Users who should receive this message')
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='team_messages',
        help_text=_('Store this message belongs to')
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='team_messages',
        help_text=_('Tenant this message belongs to')
    )

    # Threading support
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        help_text=_('Parent message for threading')
    )

    # Status
    is_urgent = models.BooleanField(
        default=False,
        help_text=_('Whether this is an urgent message')
    )
    requires_response = models.BooleanField(
        default=False,
        help_text=_('Whether this message requires a response')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Team Message')
        verbose_name_plural = _('Team Messages')
        ordering = ['-is_urgent', '-created_at']

    def __str__(self):
        return f"{self.subject} - {self.sender.username}"

    @property
    def is_reply(self):
        """Check if this is a reply to another message."""
        return self.parent_message is not None

    @property
    def thread_count(self):
        """Get the number of replies in this thread."""
        return self.replies.count()


class MessageRead(models.Model):
    """
    Track which users have read which team messages.
    """
    message = models.ForeignKey(
        TeamMessage,
        on_delete=models.CASCADE,
        related_name='reads',
        help_text=_('Message that was read')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='message_reads',
        help_text=_('User who read the message')
    )
    read_at = models.DateTimeField(auto_now_add=True)
    responded = models.BooleanField(
        default=False,
        help_text=_('Whether the user responded to the message')
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Message Read')
        verbose_name_plural = _('Message Reads')
        unique_together = ['message', 'user']
        ordering = ['-read_at']

    def __str__(self):
        return f"{self.user.username} read {self.message.subject}"

    def save(self, *args, **kwargs):
        if self.responded and not self.responded_at:
            self.responded_at = timezone.now()
        super().save(*args, **kwargs) 