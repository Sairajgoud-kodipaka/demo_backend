from rest_framework import serializers
from .models import SupportTicket, TicketMessage, SupportNotification, SupportSettings


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)
    sender_role_display = serializers.CharField(read_only=True)
    formatted_time = serializers.SerializerMethodField()

    class Meta:
        model = TicketMessage
        fields = [
            'id', 'ticket', 'sender', 'sender_name', 'sender_role', 
            'sender_role_display', 'content', 'is_internal', 'is_system_message',
            'message_type', 'created_at', 'updated_at', 'formatted_time'
        ]
        read_only_fields = ['sender', 'created_at', 'updated_at']

    def get_formatted_time(self, obj):
        try:
            return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return ''


class SupportTicketSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    messages = TicketMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    last_message_time = serializers.SerializerMethodField()
    response_time_hours = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_id', 'title', 'summary', 'category', 'priority', 'status',
            'created_by', 'created_by_name', 'assigned_to', 'assigned_to_name',
            'tenant', 'tenant_name', 'created_at', 'updated_at', 'resolved_at', 'closed_at',
            'is_urgent', 'requires_callback', 'callback_phone', 'callback_preferred_time',
            'messages', 'message_count', 'last_message_time', 'response_time_hours', 'is_overdue'
        ]
        read_only_fields = ['ticket_id', 'created_at', 'updated_at', 'resolved_at', 'closed_at']

    def get_message_count(self, obj):
        try:
            return obj.messages.count()
        except:
            return 0

    def get_last_message_time(self, obj):
        try:
            last_message = obj.messages.order_by('-created_at').first()
            return last_message.created_at if last_message else obj.created_at
        except:
            return obj.created_at

    def get_response_time_hours(self, obj):
        try:
            if obj.response_time:
                return round(obj.response_time.total_seconds() / 3600, 2)
            return None
        except:
            return None

    def get_is_overdue(self, obj):
        try:
            if obj.status in [SupportTicket.Status.OPEN, SupportTicket.Status.IN_PROGRESS]:
                from django.utils import timezone
                from datetime import timedelta
                
                # Define response time limits based on priority
                time_limits = {
                    'critical': 4,
                    'high': 8,
                    'medium': 24,
                    'low': 48
                }
                
                limit_hours = time_limits.get(obj.priority, 24)
                limit_time = obj.created_at + timedelta(hours=limit_hours)
                
                return timezone.now() > limit_time
            return False
        except:
            return False


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = [
            'title', 'summary', 'category', 'priority', 'is_urgent',
            'requires_callback', 'callback_phone', 'callback_preferred_time'
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
            validated_data['tenant'] = request.user.tenant
        
        return super().create(validated_data)


class SupportTicketUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = [
            'status', 'assigned_to', 'priority', 'category', 'is_urgent',
            'requires_callback', 'callback_phone', 'callback_preferred_time'
        ]


class TicketMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketMessage
        fields = ['ticket', 'content', 'is_internal', 'message_type']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['sender'] = request.user
        
        return super().create(validated_data)


class SupportNotificationSerializer(serializers.ModelSerializer):
    ticket_title = serializers.CharField(source='ticket.title', read_only=True)
    ticket_id = serializers.CharField(source='ticket.ticket_id', read_only=True)
    formatted_time = serializers.SerializerMethodField()

    class Meta:
        model = SupportNotification
        fields = [
            'id', 'ticket', 'ticket_title', 'ticket_id', 'notification_type',
            'title', 'message', 'is_read', 'created_at', 'formatted_time'
        ]
        read_only_fields = ['created_at']

    def get_formatted_time(self, obj):
        try:
            return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return ''


class SupportSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportSettings
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.tenant:
            validated_data['tenant'] = request.user.tenant
        
        return super().create(validated_data)


class SupportTicketSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for ticket lists and dashboards"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    message_count = serializers.SerializerMethodField()
    last_activity = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_id', 'title', 'category', 'priority', 'status',
            'created_by_name', 'assigned_to_name', 'created_at', 'updated_at',
            'is_urgent', 'message_count', 'last_activity'
        ]

    def get_message_count(self, obj):
        try:
            return obj.messages.count()
        except:
            return 0

    def get_last_activity(self, obj):
        try:
            last_message = obj.messages.order_by('-created_at').first()
            return last_message.created_at if last_message else obj.updated_at
        except:
            return obj.updated_at 