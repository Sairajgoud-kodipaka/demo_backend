from rest_framework import serializers
from .models import (
    MarketingCampaign, MessageTemplate, EcommercePlatform, 
    MarketingAnalytics, CustomerSegment, MarketingEvent
)
from apps.clients.models import Client
from apps.stores.models import Store
from apps.tenants.models import Tenant


class MarketingCampaignSerializer(serializers.ModelSerializer):
    """Serializer for MarketingCampaign model"""
    delivery_rate = serializers.ReadOnlyField()
    read_rate = serializers.ReadOnlyField()
    reply_rate = serializers.ReadOnlyField()
    conversion_rate = serializers.ReadOnlyField()
    roi = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    campaign_type_display = serializers.CharField(source='get_campaign_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = MarketingCampaign
        fields = [
            'id', 'name', 'description', 'campaign_type', 'campaign_type_display',
            'status', 'status_display', 'target_audience', 'estimated_reach',
            'message_template', 'custom_message', 'scheduled_at', 'start_date',
            'end_date', 'messages_sent', 'messages_delivered', 'messages_read',
            'replies_received', 'conversions', 'revenue_generated',
            'delivery_rate', 'read_rate', 'reply_rate', 'conversion_rate', 'roi',
            'created_by', 'created_by_name', 'tenant', 'store', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'messages_sent', 'messages_delivered', 'messages_read',
            'replies_received', 'conversions', 'revenue_generated',
            'delivery_rate', 'read_rate', 'reply_rate', 'conversion_rate', 'roi',
            'created_at', 'updated_at'
        ]


class MessageTemplateSerializer(serializers.ModelSerializer):
    """Serializer for MessageTemplate model"""
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = MessageTemplate
        fields = [
            'id', 'name', 'template_type', 'template_type_display', 'category',
            'category_display', 'subject', 'message_content', 'variables',
            'is_approved', 'approval_status', 'usage_count', 'created_by',
            'created_by_name', 'tenant', 'store', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']


class EcommercePlatformSerializer(serializers.ModelSerializer):
    """Serializer for EcommercePlatform model"""
    platform_type_display = serializers.CharField(source='get_platform_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EcommercePlatform
        fields = [
            'id', 'name', 'platform_type', 'platform_type_display', 'status',
            'status_display', 'api_key', 'api_secret', 'webhook_url', 'store_url',
            'last_sync', 'sync_frequency', 'total_products', 'total_orders',
            'total_revenue', 'tenant', 'store', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_products', 'total_orders', 'total_revenue',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'api_key': {'write_only': True},
            'api_secret': {'write_only': True}
        }


class MarketingAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for MarketingAnalytics model"""
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)

    class Meta:
        model = MarketingAnalytics
        fields = [
            'id', 'campaign', 'campaign_name', 'impressions', 'clicks',
            'conversions', 'revenue', 'age_groups', 'gender_distribution',
            'device_types', 'locations', 'date', 'hour', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerSegmentSerializer(serializers.ModelSerializer):
    """Serializer for CustomerSegment model"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = CustomerSegment
        fields = [
            'id', 'name', 'description', 'criteria', 'customer_count',
            'total_revenue', 'average_order_value', 'conversion_rate',
            'engagement_rate', 'created_by', 'created_by_name', 'tenant',
            'store', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'customer_count', 'total_revenue', 'average_order_value',
            'conversion_rate', 'engagement_rate', 'created_at', 'updated_at'
        ]


class MarketingEventSerializer(serializers.ModelSerializer):
    """Serializer for MarketingEvent model"""
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = MarketingEvent
        fields = [
            'id', 'event_type', 'event_type_display', 'title', 'description',
            'campaign', 'template', 'platform', 'segment', 'event_data',
            'tenant', 'store', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# Dashboard and Analytics Serializers
class MarketingDashboardSerializer(serializers.Serializer):
    """Serializer for marketing dashboard data"""
    total_campaigns = serializers.IntegerField()
    active_campaigns = serializers.IntegerField()
    total_reach = serializers.IntegerField()
    total_conversions = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    roi = serializers.FloatField()


class CampaignMetricsSerializer(serializers.Serializer):
    """Serializer for campaign metrics"""
    campaign_id = serializers.UUIDField()
    campaign_name = serializers.CharField()
    campaign_type = serializers.CharField()
    status = serializers.CharField()
    messages_sent = serializers.IntegerField()
    messages_delivered = serializers.IntegerField()
    messages_read = serializers.IntegerField()
    replies_received = serializers.IntegerField()
    conversions = serializers.IntegerField()
    revenue_generated = serializers.DecimalField(max_digits=12, decimal_places=2)
    delivery_rate = serializers.FloatField()
    read_rate = serializers.FloatField()
    reply_rate = serializers.FloatField()
    conversion_rate = serializers.FloatField()
    created_at = serializers.DateTimeField()


class SegmentOverviewSerializer(serializers.Serializer):
    """Serializer for segment overview data"""
    segment_id = serializers.IntegerField()
    segment_name = serializers.CharField()
    customer_count = serializers.IntegerField()
    growth = serializers.FloatField()
    conversion_rate = serializers.FloatField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)


class RealTimeAnalyticsSerializer(serializers.Serializer):
    """Serializer for real-time analytics data"""
    active_users = serializers.IntegerField()
    recent_conversions = serializers.IntegerField()
    campaign_performance = serializers.ListField(child=serializers.DictField())


class EcommerceSummarySerializer(serializers.Serializer):
    """Serializer for e-commerce summary data"""
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_orders = serializers.IntegerField()
    customers = serializers.IntegerField()
    avg_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    conversion_rate = serializers.FloatField()
    platforms = serializers.ListField(child=serializers.DictField())
    recent_orders = serializers.ListField(child=serializers.DictField())


class WhatsAppMetricsSerializer(serializers.Serializer):
    """Serializer for WhatsApp metrics"""
    messages_sent = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    messages_read = serializers.IntegerField()
    read_rate = serializers.FloatField()
    replies = serializers.IntegerField()
    reply_rate = serializers.FloatField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    conversion_rate = serializers.FloatField()
    campaigns = serializers.ListField(child=serializers.DictField())


# Nested Serializers for Related Data
class CampaignListSerializer(serializers.ModelSerializer):
    """Simplified serializer for campaign lists"""
    campaign_type_display = serializers.CharField(source='get_campaign_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    delivery_rate = serializers.ReadOnlyField()
    read_rate = serializers.ReadOnlyField()
    conversion_rate = serializers.ReadOnlyField()

    class Meta:
        model = MarketingCampaign
        fields = [
            'id', 'name', 'campaign_type', 'campaign_type_display', 'status',
            'status_display', 'estimated_reach', 'messages_sent', 'messages_delivered',
            'messages_read', 'conversions', 'revenue_generated', 'delivery_rate',
            'read_rate', 'conversion_rate', 'scheduled_at', 'created_at'
        ]


class TemplateListSerializer(serializers.ModelSerializer):
    """Simplified serializer for template lists"""
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = MessageTemplate
        fields = [
            'id', 'name', 'template_type', 'template_type_display', 'category',
            'category_display', 'is_approved', 'approval_status', 'usage_count',
            'created_at'
        ]


class PlatformListSerializer(serializers.ModelSerializer):
    """Simplified serializer for platform lists"""
    platform_type_display = serializers.CharField(source='get_platform_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EcommercePlatform
        fields = [
            'id', 'name', 'platform_type', 'platform_type_display', 'status',
            'status_display', 'total_products', 'total_orders', 'total_revenue',
            'last_sync', 'created_at'
        ] 