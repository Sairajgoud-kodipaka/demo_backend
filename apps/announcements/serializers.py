from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Announcement, AnnouncementRead, TeamMessage, MessageRead

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user information in announcements."""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'role']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class StoreSerializer(serializers.ModelSerializer):
    """Serializer for store information in announcements."""
    class Meta:
        model = User._meta.get_field('store').related_model
        fields = ['id', 'name', 'code']


class TenantSerializer(serializers.ModelSerializer):
    """Serializer for tenant information in announcements."""
    class Meta:
        model = User._meta.get_field('tenant').related_model
        fields = ['id', 'name', 'slug']


class AnnouncementReadSerializer(serializers.ModelSerializer):
    """Serializer for announcement read tracking."""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = AnnouncementRead
        fields = ['id', 'user', 'read_at', 'acknowledged', 'acknowledged_at']


class AnnouncementSerializer(serializers.ModelSerializer):
    """Serializer for announcements."""
    author = UserSerializer(read_only=True)
    tenant = TenantSerializer(read_only=True)
    target_stores = StoreSerializer(many=True, read_only=True)
    target_tenants = TenantSerializer(many=True, read_only=True)
    reads = AnnouncementReadSerializer(many=True, read_only=True)
    read_count = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    is_read_by_current_user = serializers.SerializerMethodField()
    is_acknowledged_by_current_user = serializers.SerializerMethodField()
    priority_color = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content', 'announcement_type', 'priority', 'priority_color',
            'target_roles', 'target_stores', 'target_tenants', 'is_pinned', 'is_active',
            'requires_acknowledgment', 'publish_at', 'expires_at', 'author', 'tenant',
            'created_at', 'updated_at', 'reads', 'read_count', 'unread_count',
            'is_read_by_current_user', 'is_acknowledged_by_current_user'
        ]
        read_only_fields = ['author', 'tenant', 'created_at', 'updated_at', 'reads']
    
    def get_read_count(self, obj):
        return obj.reads.count()
    
    def get_unread_count(self, obj):
        # This would need to be calculated based on target users
        # For now, return 0 as it's complex to calculate
        return 0
    
    def get_is_read_by_current_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.reads.filter(user=request.user).exists()
        return False
    
    def get_is_acknowledged_by_current_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            read_record = obj.reads.filter(user=request.user).first()
            return read_record.acknowledged if read_record else False
        return False
    
    def get_priority_color(self, obj):
        return obj.get_priority_color()


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating announcements."""
    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'announcement_type', 'priority', 'target_roles',
            'target_stores', 'target_tenants', 'is_pinned', 'is_active',
            'requires_acknowledgment', 'publish_at', 'expires_at'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['author'] = request.user
        validated_data['tenant'] = request.user.tenant
        return super().create(validated_data)


class AnnouncementUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating announcements."""
    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'announcement_type', 'priority', 'target_roles',
            'target_stores', 'target_tenants', 'is_pinned', 'is_active',
            'requires_acknowledgment', 'publish_at', 'expires_at'
        ]


class MessageReadSerializer(serializers.ModelSerializer):
    """Serializer for message read tracking."""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = MessageRead
        fields = ['id', 'user', 'read_at', 'responded', 'responded_at']


class TeamMessageSerializer(serializers.ModelSerializer):
    """Serializer for team messages."""
    sender = UserSerializer(read_only=True)
    recipients = UserSerializer(many=True, read_only=True)
    store = StoreSerializer(read_only=True)
    tenant = TenantSerializer(read_only=True)
    parent_message = serializers.PrimaryKeyRelatedField(read_only=True)
    replies = serializers.SerializerMethodField()
    reads = MessageReadSerializer(many=True, read_only=True)
    read_count = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    is_read_by_current_user = serializers.SerializerMethodField()
    is_responded_by_current_user = serializers.SerializerMethodField()
    thread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamMessage
        fields = [
            'id', 'subject', 'content', 'message_type', 'sender', 'recipients',
            'store', 'tenant', 'parent_message', 'replies', 'is_urgent',
            'requires_response', 'created_at', 'updated_at', 'reads', 'read_count',
            'unread_count', 'is_read_by_current_user', 'is_responded_by_current_user',
            'thread_count'
        ]
        read_only_fields = ['sender', 'store', 'tenant', 'created_at', 'updated_at', 'reads']
    
    def get_replies(self, obj):
        # Only include basic info for replies to avoid circular references
        return [
            {
                'id': reply.id,
                'subject': reply.subject,
                'sender': UserSerializer(reply.sender).data,
                'created_at': reply.created_at
            }
            for reply in obj.replies.all()[:5]  # Limit to 5 most recent replies
        ]
    
    def get_read_count(self, obj):
        return obj.reads.count()
    
    def get_unread_count(self, obj):
        # Calculate based on recipients who haven't read
        recipient_count = obj.recipients.count()
        read_count = obj.reads.count()
        return max(0, recipient_count - read_count)
    
    def get_is_read_by_current_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.reads.filter(user=request.user).exists()
        return False
    
    def get_is_responded_by_current_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            read_record = obj.reads.filter(user=request.user).first()
            return read_record.responded if read_record else False
        return False
    
    def get_thread_count(self, obj):
        return obj.thread_count


class TeamMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating team messages."""
    class Meta:
        model = TeamMessage
        fields = [
            'subject', 'content', 'message_type', 'parent_message',
            'is_urgent', 'requires_response'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['sender'] = request.user
        validated_data['tenant'] = request.user.tenant
        
        # Handle store assignment - use user's store if available, otherwise get first store from tenant
        if request.user.store:
            validated_data['store'] = request.user.store
        else:
            # If user doesn't have a store, get the first store from their tenant
            from apps.stores.models import Store
            first_store = Store.objects.filter(tenant=request.user.tenant).first()
            if first_store:
                validated_data['store'] = first_store
            else:
                # If no store exists, create a default store for the tenant
                first_store = Store.objects.create(
                    name=f"{request.user.tenant.name} - Main Store",
                    code="MAIN",
                    tenant=request.user.tenant,
                    is_active=True
                )
                validated_data['store'] = first_store
        
        # Create the message first
        message = super().create(validated_data)
        
        # Automatically assign all team members of the same store as recipients
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get all users in the same store (excluding the sender)
        store_users = User.objects.filter(
            store=message.store,
            is_active=True
        ).exclude(id=request.user.id)
        
        # Add them as recipients
        message.recipients.set(store_users)
        
        return message


class TeamMessageUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating team messages."""
    class Meta:
        model = TeamMessage
        fields = [
            'subject', 'content', 'message_type', 'recipients', 'is_urgent',
            'requires_response'
        ]


class AnnouncementReadCreateSerializer(serializers.ModelSerializer):
    """Serializer for marking announcements as read."""
    class Meta:
        model = AnnouncementRead
        fields = ['announcement', 'acknowledged']
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class MessageReadCreateSerializer(serializers.ModelSerializer):
    """Serializer for marking messages as read."""
    class Meta:
        model = MessageRead
        fields = ['message', 'responded']
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data) 