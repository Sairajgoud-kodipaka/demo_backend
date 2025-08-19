from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    WhatsAppSession, WhatsAppContact, WhatsAppMessage, WhatsAppBot,
    WhatsAppBotTrigger, WhatsAppCampaign, WhatsAppTeamMember,
    WhatsAppConversation, WhatsAppAnalytics
)

@admin.register(WhatsAppSession)
class WhatsAppSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'status', 'assigned_team_member', 'messages_sent', 'messages_received', 'last_activity']
    list_filter = ['status', 'auto_reply_enabled', 'business_hours_enabled', 'created_at']
    search_fields = ['name', 'phone_number', 'assigned_team_member__user__username']
    readonly_fields = ['session_id', 'created_at', 'updated_at', 'last_activity']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'phone_number', 'session_id', 'status')
        }),
        ('Team Assignment', {
            'fields': ('assigned_team_member',)
        }),
        ('Configuration', {
            'fields': ('auto_reply_enabled', 'business_hours_enabled', 'business_hours_start', 'business_hours_end')
        }),
        ('Statistics', {
            'fields': ('messages_sent', 'messages_received', 'last_activity')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('assigned_team_member__user')


@admin.register(WhatsAppContact)
class WhatsAppContactAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'name', 'customer_type', 'status', 'total_messages', 'total_orders', 'total_spent', 'last_interaction']
    list_filter = ['status', 'customer_type', 'language', 'created_at', 'opt_in_date']
    search_fields = ['phone_number', 'name', 'email']
    readonly_fields = ['created_at', 'updated_at', 'opt_in_date', 'last_interaction']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('phone_number', 'name', 'email', 'status')
        }),
        ('Customer Details', {
            'fields': ('customer_type', 'language', 'timezone')
        }),
        ('Statistics', {
            'fields': ('total_messages', 'total_orders', 'total_spent')
        }),
        ('Segmentation', {
            'fields': ('tags',)
        }),
        ('Timestamps', {
            'fields': ('opt_in_date', 'last_interaction', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ['contact_phone', 'direction', 'type', 'content_preview', 'status', 'is_bot_response', 'sent_at']
    list_filter = ['direction', 'type', 'status', 'is_bot_response', 'created_at']
    search_fields = ['contact__phone_number', 'contact__name', 'content']
    readonly_fields = ['message_id', 'created_at', 'updated_at', 'sent_at', 'delivered_at', 'read_at']
    
    fieldsets = (
        ('Message Details', {
            'fields': ('message_id', 'session', 'contact', 'direction', 'type', 'content', 'media_url')
        }),
        ('Status Tracking', {
            'fields': ('status', 'sent_at', 'delivered_at', 'read_at')
        }),
        ('Metadata', {
            'fields': ('is_bot_response', 'bot_trigger', 'campaign_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def contact_phone(self, obj):
        return obj.contact.phone_number if obj.contact else 'Unknown'
    contact_phone.short_description = 'Contact Phone'
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('contact', 'session')


@admin.register(WhatsAppBot)
class WhatsAppBotAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'max_conversation_turns', 'business_hours_only', 'created_at']
    list_filter = ['status', 'business_hours_only', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Bot Configuration', {
            'fields': ('name', 'description', 'status')
        }),
        ('Behavior Settings', {
            'fields': ('welcome_message', 'fallback_message', 'max_conversation_turns')
        }),
        ('Operating Hours', {
            'fields': ('business_hours_only', 'after_hours_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(WhatsAppBotTrigger)
class WhatsAppBotTriggerAdmin(admin.ModelAdmin):
    list_display = ['name', 'bot', 'trigger_type', 'trigger_value', 'priority', 'is_active', 'requires_human_handoff']
    list_filter = ['trigger_type', 'is_active', 'requires_human_handoff', 'priority', 'created_at']
    search_fields = ['name', 'trigger_value', 'response_message']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Trigger Configuration', {
            'fields': ('bot', 'name', 'trigger_type', 'trigger_value', 'priority')
        }),
        ('Response Settings', {
            'fields': ('response_message', 'response_type', 'media_url')
        }),
        ('Advanced Features', {
            'fields': ('requires_human_handoff', 'handoff_message', 'min_confidence')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('bot')


@admin.register(WhatsAppCampaign)
class WhatsAppCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'campaign_type', 'status', 'total_recipients', 'messages_sent', 'delivery_rate', 'read_rate', 'created_at']
    list_filter = ['campaign_type', 'status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'total_recipients', 'messages_sent', 'messages_delivered', 'messages_read', 'replies_received']
    
    fieldsets = (
        ('Campaign Information', {
            'fields': ('name', 'description', 'campaign_type', 'status')
        }),
        ('Content', {
            'fields': ('message_template', 'target_audience')
        }),
        ('Scheduling', {
            'fields': ('scheduled_at',)
        }),
        ('Statistics', {
            'fields': ('total_recipients', 'messages_sent', 'messages_delivered', 'messages_read', 'replies_received')
        }),
        ('Performance Metrics', {
            'fields': ('delivery_rate', 'read_rate', 'reply_rate')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def delivery_rate(self, obj):
        if obj.total_recipients > 0:
            rate = (obj.messages_delivered / obj.total_recipients) * 100
            return f"{rate:.1f}%"
        return "0%"
    delivery_rate.short_description = 'Delivery Rate'
    
    def read_rate(self, obj):
        if obj.messages_delivered > 0:
            rate = (obj.messages_read / obj.messages_delivered) * 100
            return f"{rate:.1f}%"
        return "0%"
    read_rate.short_description = 'Read Rate'


@admin.register(WhatsAppTeamMember)
class WhatsAppTeamMemberAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'role', 'status', 'is_online', 'total_messages_sent', 'total_customers_helped', 'customer_satisfaction_score', 'last_seen']
    list_filter = ['role', 'status', 'is_online', 'can_send_messages', 'can_manage_campaigns', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'last_seen']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role', 'status')
        }),
        ('Permissions', {
            'fields': ('can_send_messages', 'can_manage_campaigns', 'can_manage_bots', 'can_manage_team', 'can_view_analytics')
        }),
        ('Performance Tracking', {
            'fields': ('total_messages_sent', 'total_customers_helped', 'average_response_time', 'customer_satisfaction_score')
        }),
        ('Availability', {
            'fields': ('is_online', 'working_hours', 'last_seen')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def user_name(self, obj):
        return obj.user.get_full_name() if obj.user else 'Unknown'
    user_name.short_description = 'User Name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(admin.ModelAdmin):
    list_display = ['contact_info', 'status', 'priority', 'assigned_agent', 'first_message_at', 'last_message_at', 'resolution_time']
    list_filter = ['status', 'priority', 'category', 'created_at']
    search_fields = ['contact__phone_number', 'contact__name', 'subject']
    readonly_fields = ['created_at', 'updated_at', 'first_message_at', 'last_message_at']
    
    fieldsets = (
        ('Conversation Details', {
            'fields': ('contact', 'session', 'status', 'priority', 'subject')
        }),
        ('Assignment', {
            'fields': ('assigned_agent',)
        }),
        ('Tracking', {
            'fields': ('first_message_at', 'last_message_at', 'resolution_time')
        }),
        ('Categorization', {
            'fields': ('tags', 'category')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def contact_info(self, obj):
        if obj.contact:
            return f"{obj.contact.name or 'Unknown'} ({obj.contact.phone_number})"
        return 'Unknown Contact'
    contact_info.short_description = 'Contact'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('contact', 'session', 'assigned_agent__user')


@admin.register(WhatsAppAnalytics)
class WhatsAppAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_messages_sent', 'total_messages_received', 'messages_delivered', 'messages_read', 'new_contacts', 'active_conversations']
    list_filter = ['date', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Date', {
            'fields': ('date',)
        }),
        ('Message Statistics', {
            'fields': ('total_messages_sent', 'total_messages_received', 'messages_delivered', 'messages_read', 'messages_failed')
        }),
        ('Response Metrics', {
            'fields': ('average_response_time', 'first_response_time', 'resolution_time')
        }),
        ('Customer Metrics', {
            'fields': ('new_contacts', 'active_conversations', 'resolved_conversations')
        }),
        ('Campaign Performance', {
            'fields': ('campaigns_sent', 'campaign_delivery_rate', 'campaign_read_rate')
        }),
        ('Bot Performance', {
            'fields': ('bot_interactions', 'bot_resolution_rate', 'human_handoffs')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        # Analytics are typically auto-generated, not manually created
        return False


# Custom admin site configuration
admin.site.site_header = "WhatsApp Business Admin"
admin.site.site_title = "WhatsApp Business"
admin.site.index_title = "WhatsApp Business Administration"

# Register models with custom admin classes
admin.site.register(WhatsAppSession, WhatsAppSessionAdmin)
admin.site.register(WhatsAppContact, WhatsAppContactAdmin)
admin.site.register(WhatsAppMessage, WhatsAppMessageAdmin)
admin.site.register(WhatsAppBot, WhatsAppBotAdmin)
admin.site.register(WhatsAppBotTrigger, WhatsAppBotTriggerAdmin)
admin.site.register(WhatsAppCampaign, WhatsAppCampaignAdmin)
admin.site.register(WhatsAppTeamMember, WhatsAppTeamMemberAdmin)
admin.site.register(WhatsAppConversation, WhatsAppConversationAdmin)
admin.site.register(WhatsAppAnalytics, WhatsAppAnalyticsAdmin)
