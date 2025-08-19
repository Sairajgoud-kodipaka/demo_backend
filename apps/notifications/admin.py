from django.contrib import admin
from .models import Notification, NotificationSettings


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'user', 'tenant', 'status', 'priority', 'created_at']
    list_filter = ['type', 'status', 'priority', 'tenant', 'created_at']
    search_fields = ['title', 'message', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'read_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'message', 'type', 'priority', 'status')
        }),
        ('Relationships', {
            'fields': ('user', 'tenant', 'store')
        }),
        ('Action Details', {
            'fields': ('action_url', 'action_text', 'is_persistent')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'read_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'tenant', 'email_enabled', 'push_enabled', 'in_app_enabled']
    list_filter = ['email_enabled', 'push_enabled', 'in_app_enabled', 'tenant']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'tenant')
        }),
        ('Email Notifications', {
            'fields': ('email_enabled', 'email_types', 'email_frequency')
        }),
        ('Push Notifications', {
            'fields': ('push_enabled', 'push_types')
        }),
        ('In-App Notifications', {
            'fields': ('in_app_enabled', 'in_app_types', 'in_app_sound', 'in_app_desktop')
        }),
        ('Quiet Hours', {
            'fields': ('quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end', 'quiet_hours_timezone')
        }),
        ('Preferences', {
            'fields': (
                'appointment_reminders', 'deal_updates', 'order_notifications',
                'inventory_alerts', 'task_reminders', 'announcements',
                'escalations', 'marketing_updates'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ) 