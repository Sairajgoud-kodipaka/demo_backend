from rest_framework import serializers
from .models import Escalation, EscalationNote, EscalationTemplate
from apps.users.serializers import UserSerializer
from apps.clients.serializers import ClientSerializer


class EscalationNoteSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = EscalationNote
        fields = '__all__'
        read_only_fields = ('created_at',)


class EscalationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalationTemplate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class EscalationSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    notes = EscalationNoteSerializer(many=True, read_only=True)
    is_overdue = serializers.ReadOnlyField()
    time_to_resolution = serializers.ReadOnlyField()
    sla_compliance = serializers.ReadOnlyField()
    client_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Escalation
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'assigned_at', 'resolved_at', 'closed_at', 'due_date')

    def get_client_name(self, obj):
        if obj.client:
            return f"{obj.client.first_name} {obj.client.last_name}".strip()
        return "Unknown Client"

    def create(self, validated_data):
        # Set the created_by field to the current user
        validated_data['created_by'] = self.context['request'].user
        validated_data['tenant'] = self.context['request'].user.tenant
        return super().create(validated_data)


class EscalationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Escalation
        fields = ['title', 'description', 'category', 'priority', 'client', 'sla_hours']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['tenant'] = self.context['request'].user.tenant
        return super().create(validated_data)


class EscalationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Escalation
        fields = ['title', 'description', 'category', 'priority', 'status', 'assigned_to', 'sla_hours']


class EscalationNoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalationNote
        fields = ['content', 'is_internal']

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['escalation_id'] = self.context['escalation_id']
        return super().create(validated_data)


class EscalationStatsSerializer(serializers.Serializer):
    total_escalations = serializers.IntegerField()
    open_escalations = serializers.IntegerField()
    overdue_escalations = serializers.IntegerField()
    resolved_today = serializers.IntegerField()
    avg_resolution_time = serializers.FloatField()
    sla_compliance_rate = serializers.FloatField()
    escalations_by_priority = serializers.DictField()
    escalations_by_category = serializers.DictField()
    escalations_by_status = serializers.DictField() 