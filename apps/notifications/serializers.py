from rest_framework import serializers
from .models import Notification, NotificationSettings


class NotificationSerializer(serializers.ModelSerializer):
    userId = serializers.IntegerField(source='user.id', read_only=True)
    tenantId = serializers.IntegerField(source='tenant.id', read_only=True)
    storeId = serializers.IntegerField(source='store.id', read_only=True, allow_null=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    readAt = serializers.DateTimeField(source='read_at', read_only=True, allow_null=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    actionUrl = serializers.CharField(source='action_url', read_only=True, allow_null=True)
    actionText = serializers.CharField(source='action_text', read_only=True, allow_null=True)
    isPersistent = serializers.BooleanField(source='is_persistent', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'title', 'message', 'priority', 'status',
            'userId', 'tenantId', 'storeId', 'actionUrl', 'actionText',
            'isPersistent', 'createdAt', 'readAt', 'updatedAt'
        ]
        read_only_fields = ['id', 'createdAt', 'readAt', 'updatedAt']


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        fields = [
            'id', 'user', 'tenant', 'email_enabled', 'email_types',
            'email_frequency', 'push_enabled', 'push_types',
            'in_app_enabled', 'in_app_types', 'in_app_sound',
            'in_app_desktop', 'quiet_hours_enabled', 'quiet_hours_start',
            'quiet_hours_end', 'quiet_hours_timezone', 'appointment_reminders',
            'deal_updates', 'order_notifications', 'inventory_alerts',
            'task_reminders', 'announcements', 'escalations',
            'marketing_updates', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'type', 'title', 'message', 'priority', 'status',
            'user', 'tenant', 'store', 'action_url', 'action_text',
            'is_persistent'
        ]


class NotificationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['status', 'read_at']
        read_only_fields = ['read_at'] 