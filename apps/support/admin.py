from django.contrib import admin
from .models import SupportTicket, TicketMessage, SupportNotification, SupportSettings


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'title', 'category', 'priority', 'status', 'created_by', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'category', 'created_at', 'tenant']
    search_fields = ['ticket_id', 'title', 'summary', 'created_by__username']
    readonly_fields = ['ticket_id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    list_select_related = ['created_by', 'assigned_to']


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'sender', 'message_type', 'is_internal', 'is_system_message', 'created_at']
    list_filter = ['message_type', 'is_internal', 'is_system_message', 'created_at']
    search_fields = ['content', 'ticket__ticket_id', 'sender__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SupportNotification)
class SupportNotificationAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'recipient', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['ticket__ticket_id', 'recipient__username', 'title']
    readonly_fields = ['created_at']


@admin.register(SupportSettings)
class SupportSettingsAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'auto_assign_tickets', 'max_response_time_hours', 'email_notifications']
    list_filter = ['auto_assign_tickets', 'email_notifications', 'in_app_notifications', 'sms_notifications']
    search_fields = ['tenant__name'] 