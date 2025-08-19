from django.contrib import admin
from .models import (
    MarketingCampaign, MessageTemplate, EcommercePlatform, 
    MarketingAnalytics, CustomerSegment, MarketingEvent
)


@admin.register(MarketingCampaign)
class MarketingCampaignAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'campaign_type', 'status', 'estimated_reach', 
        'messages_sent', 'conversions', 'revenue_generated', 'created_by', 'created_at'
    ]
    list_filter = ['campaign_type', 'status', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = [
        'id', 'messages_sent', 'messages_delivered', 'messages_read',
        'replies_received', 'conversions', 'revenue_generated',
        'delivery_rate', 'read_rate', 'reply_rate', 'conversion_rate', 'roi'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'campaign_type', 'status')
        }),
        ('Targeting', {
            'fields': ('target_audience', 'estimated_reach')
        }),
        ('Content', {
            'fields': ('message_template', 'custom_message')
        }),
        ('Scheduling', {
            'fields': ('scheduled_at', 'start_date', 'end_date')
        }),
        ('Performance Metrics', {
            'fields': (
                'messages_sent', 'messages_delivered', 'messages_read',
                'replies_received', 'conversions', 'revenue_generated'
            ),
            'classes': ('collapse',)
        }),
        ('Calculated Metrics', {
            'fields': (
                'delivery_rate', 'read_rate', 'reply_rate', 'conversion_rate', 'roi'
            ),
            'classes': ('collapse',)
        }),
        ('Relationships', {
            'fields': ('created_by', 'tenant', 'store')
        }),
    )


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'template_type', 'category', 'is_approved', 
        'approval_status', 'usage_count', 'created_by', 'created_at'
    ]
    list_filter = ['template_type', 'category', 'is_approved', 'approval_status', 'created_at']
    search_fields = ['name', 'message_content', 'created_by__username']
    readonly_fields = ['id', 'usage_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'template_type', 'category')
        }),
        ('Content', {
            'fields': ('subject', 'message_content', 'variables')
        }),
        ('Approval Status', {
            'fields': ('is_approved', 'approval_status')
        }),
        ('Usage', {
            'fields': ('usage_count',)
        }),
        ('Relationships', {
            'fields': ('created_by', 'tenant', 'store')
        }),
    )


@admin.register(EcommercePlatform)
class EcommercePlatformAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'platform_type', 'status', 'total_products', 
        'total_orders', 'total_revenue', 'last_sync', 'created_at'
    ]
    list_filter = ['platform_type', 'status', 'created_at']
    search_fields = ['name', 'store_url']
    readonly_fields = [
        'id', 'total_products', 'total_orders', 'total_revenue'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'platform_type', 'status')
        }),
        ('Connection Details', {
            'fields': ('api_key', 'api_secret', 'webhook_url', 'store_url')
        }),
        ('Sync Information', {
            'fields': ('last_sync', 'sync_frequency')
        }),
        ('Statistics', {
            'fields': ('total_products', 'total_orders', 'total_revenue')
        }),
        ('Relationships', {
            'fields': ('tenant', 'store')
        }),
    )


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'customer_count', 'total_revenue', 'average_order_value',
        'conversion_rate', 'engagement_rate', 'created_by', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = [
        'id', 'customer_count', 'total_revenue', 'average_order_value',
        'conversion_rate', 'engagement_rate'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Segment Criteria', {
            'fields': ('criteria',)
        }),
        ('Statistics', {
            'fields': (
                'customer_count', 'total_revenue', 'average_order_value',
                'conversion_rate', 'engagement_rate'
            )
        }),
        ('Relationships', {
            'fields': ('created_by', 'tenant', 'store')
        }),
    )


@admin.register(MarketingAnalytics)
class MarketingAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'campaign', 'date', 'hour', 'impressions', 'clicks', 
        'conversions', 'revenue', 'created_at'
    ]
    list_filter = ['date', 'campaign__campaign_type', 'created_at']
    search_fields = ['campaign__name']
    readonly_fields = ['id']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Campaign', {
            'fields': ('campaign',)
        }),
        ('Metrics', {
            'fields': ('impressions', 'clicks', 'conversions', 'revenue')
        }),
        ('Demographics', {
            'fields': ('age_groups', 'gender_distribution', 'device_types', 'locations'),
            'classes': ('collapse',)
        }),
        ('Time', {
            'fields': ('date', 'hour')
        }),
    )


@admin.register(MarketingEvent)
class MarketingEventAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'title', 'campaign', 'template', 'platform', 
        'segment', 'created_at'
    ]
    list_filter = ['event_type', 'created_at']
    search_fields = ['title', 'description', 'campaign__name']
    readonly_fields = ['id']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Event Information', {
            'fields': ('event_type', 'title', 'description')
        }),
        ('Related Objects', {
            'fields': ('campaign', 'template', 'platform', 'segment')
        }),
        ('Event Data', {
            'fields': ('event_data',)
        }),
        ('Relationships', {
            'fields': ('tenant', 'store')
        }),
    )
