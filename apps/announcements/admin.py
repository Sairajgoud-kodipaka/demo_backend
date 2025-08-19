from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Announcement, AnnouncementRead, TeamMessage, MessageRead


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'announcement_type', 'priority', 'author', 'tenant',
        'is_pinned', 'is_active', 'is_published', 'read_count_display', 'created_at'
    ]
    list_filter = [
        'announcement_type', 'priority', 'is_pinned', 'is_active',
        'requires_acknowledgment', 'created_at', 'publish_at', 'expires_at'
    ]
    search_fields = ['title', 'content', 'author__username', 'author__first_name', 'author__last_name']
    readonly_fields = ['created_at', 'updated_at', 'read_count_display']
    filter_horizontal = ['target_stores', 'target_tenants']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'content', 'announcement_type', 'priority')
        }),
        ('Targeting', {
            'fields': ('target_roles', 'target_stores', 'target_tenants'),
            'classes': ('collapse',)
        }),
        ('Visibility & Scheduling', {
            'fields': ('is_pinned', 'is_active', 'requires_acknowledgment', 'publish_at', 'expires_at')
        }),
        ('Metadata', {
            'fields': ('author', 'tenant', 'created_at', 'updated_at', 'read_count_display'),
            'classes': ('collapse',)
        }),
    )
    
    def read_count_display(self, obj):
        return obj.reads.count()
    read_count_display.short_description = 'Read Count'
    
    def is_published(self, obj):
        if obj.is_published:
            return format_html('<span style="color: green;">✓ Published</span>')
        else:
            return format_html('<span style="color: red;">✗ Not Published</span>')
    is_published.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set author on creation
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(AnnouncementRead)
class AnnouncementReadAdmin(admin.ModelAdmin):
    list_display = ['announcement', 'user', 'read_at', 'acknowledged', 'acknowledged_at']
    list_filter = ['acknowledged', 'read_at', 'acknowledged_at']
    search_fields = [
        'announcement__title', 'user__username', 'user__first_name', 'user__last_name'
    ]
    readonly_fields = ['read_at', 'acknowledged_at']
    
    def has_add_permission(self, request):
        return False  # Read records are created automatically


@admin.register(TeamMessage)
class TeamMessageAdmin(admin.ModelAdmin):
    list_display = [
        'subject', 'message_type', 'sender', 'store', 'tenant',
        'is_urgent', 'requires_response', 'thread_count', 'created_at'
    ]
    list_filter = [
        'message_type', 'is_urgent', 'requires_response', 'created_at'
    ]
    search_fields = [
        'subject', 'content', 'sender__username', 'sender__first_name', 'sender__last_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'thread_count_display']
    filter_horizontal = ['recipients']
    
    fieldsets = (
        ('Message Content', {
            'fields': ('subject', 'content', 'message_type')
        }),
        ('Recipients & Targeting', {
            'fields': ('sender', 'recipients', 'store', 'tenant', 'parent_message')
        }),
        ('Message Settings', {
            'fields': ('is_urgent', 'requires_response')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'thread_count_display'),
            'classes': ('collapse',)
        }),
    )
    
    def thread_count_display(self, obj):
        return obj.thread_count
    thread_count_display.short_description = 'Replies'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set sender on creation
            obj.sender = request.user
        super().save_model(request, obj, form, change)


@admin.register(MessageRead)
class MessageReadAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'read_at', 'responded', 'responded_at']
    list_filter = ['responded', 'read_at', 'responded_at']
    search_fields = [
        'message__subject', 'user__username', 'user__first_name', 'user__last_name'
    ]
    readonly_fields = ['read_at', 'responded_at']
    
    def has_add_permission(self, request):
        return False  # Read records are created automatically 