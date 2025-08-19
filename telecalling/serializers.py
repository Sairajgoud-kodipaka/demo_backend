from rest_framework import serializers
from .models import (
    CustomerVisit, Assignment, CallLog, FollowUp, 
    CustomerProfile, Notification, Analytics
)
from django.contrib.auth import get_user_model

User = get_user_model()

class UserMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

class CustomerVisitSerializer(serializers.ModelSerializer):
    sales_rep_details = UserMiniSerializer(source='sales_rep', read_only=True)
    
    class Meta:
        model = CustomerVisit
        fields = [
            'id', 'sales_rep', 'sales_rep_details', 'customer_name', 'customer_phone', 
            'customer_email', 'interests', 'visit_timestamp', 'notes', 'lead_quality',
            'assigned_to_telecaller', 'created_at', 'updated_at'
        ]
        read_only_fields = ['sales_rep', 'created_at', 'updated_at']

class CallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallLog
        fields = [
            'id', 'assignment', 'call_status', 'call_duration', 'feedback',
            'customer_sentiment', 'revisit_required', 'revisit_notes', 'recording_url',
            'disposition_code', 'call_time', 'created_at', 'updated_at'
        ]
        read_only_fields = ['call_time', 'created_at', 'updated_at']

class AssignmentSerializer(serializers.ModelSerializer):
    telecaller_details = UserMiniSerializer(source='telecaller', read_only=True)
    assigned_by_details = UserMiniSerializer(source='assigned_by', read_only=True)
    customer_visit_details = CustomerVisitSerializer(source='customer_visit', read_only=True)
    call_logs = CallLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Assignment
        fields = [
            'id', 'telecaller', 'telecaller_details', 'customer_visit', 'customer_visit_details',
            'assigned_by', 'assigned_by_details', 'status', 'priority', 'scheduled_time',
            'notes', 'outcome', 'call_logs', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class FollowUpSerializer(serializers.ModelSerializer):
    created_by_details = UserMiniSerializer(source='created_by', read_only=True)
    
    class Meta:
        model = FollowUp
        fields = [
            'id', 'assignment', 'scheduled_time', 'notes', 'status', 'priority',
            'completed_time', 'created_by', 'created_by_details', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class CustomerProfileSerializer(serializers.ModelSerializer):
    customer_visit_details = CustomerVisitSerializer(source='customer_visit', read_only=True)
    
    class Meta:
        model = CustomerProfile
        fields = [
            'id', 'customer_visit', 'customer_visit_details', 'original_notes',
            'telecaller_feedback', 'engagement_score', 'conversion_likelihood',
            'last_contact_date', 'next_follow_up_date', 'tags', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class NotificationSerializer(serializers.ModelSerializer):
    recipient_details = UserMiniSerializer(source='recipient', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_details', 'title', 'message', 'notification_type',
            'related_assignment', 'is_read', 'created_at'
        ]
        read_only_fields = ['created_at']

class AnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analytics
        fields = [
            'id', 'date', 'total_leads', 'assigned_leads', 'connected_calls',
            'conversions', 'avg_call_duration', 'engagement_score_avg', 'conversion_rate',
            'created_at'
        ]
        read_only_fields = ['created_at']

# Bulk assignment serializer
class BulkAssignmentSerializer(serializers.Serializer):
    telecaller_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of telecaller user IDs"
    )
    customer_visit_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of customer visit IDs to assign"
    )
    priority = serializers.ChoiceField(
        choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')],
        default='medium'
    )
    notes = serializers.CharField(required=False, allow_blank=True)

# Assignment statistics serializer
class AssignmentStatsSerializer(serializers.Serializer):
    total_assignments = serializers.IntegerField()
    completed_assignments = serializers.IntegerField()
    pending_assignments = serializers.IntegerField()
    follow_up_assignments = serializers.IntegerField()
    total_calls = serializers.IntegerField()
    conversions = serializers.IntegerField()
    avg_call_duration = serializers.FloatField()
    conversion_rate = serializers.FloatField()
    engagement_score_avg = serializers.FloatField()

# Dashboard data serializer
class DashboardDataSerializer(serializers.Serializer):
    today_leads = serializers.IntegerField()
    pending_assignments = serializers.IntegerField()
    completed_calls = serializers.IntegerField()
    high_potential_leads = serializers.IntegerField()
    unconnected_calls = serializers.IntegerField()
    recent_activities = serializers.ListField()
    performance_metrics = serializers.DictField() 