from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Goal, WorkTask, TaskComment, TaskAttachment

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email', 'role']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class GoalSerializer(serializers.ModelSerializer):
    """Serializer for Goal model."""
    assigned_to = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = Goal
        fields = [
            'id', 'title', 'description', 'goal_type', 'period', 'target_value',
            'current_value', 'start_date', 'end_date', 'assigned_to', 'store',
            'is_active', 'is_completed', 'created_at', 'updated_at', 'created_by',
            'progress_percentage', 'is_overdue', 'days_remaining'
        ]
        read_only_fields = ['created_at', 'updated_at', 'progress_percentage', 'is_overdue', 'days_remaining']


class GoalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating goals."""
    
    class Meta:
        model = Goal
        fields = [
            'title', 'description', 'goal_type', 'period', 'target_value',
            'start_date', 'end_date', 'assigned_to', 'store'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class GoalUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating goals."""
    
    class Meta:
        model = Goal
        fields = [
            'title', 'description', 'goal_type', 'period', 'target_value',
            'current_value', 'start_date', 'end_date', 'assigned_to', 'store',
            'is_active', 'is_completed'
        ]


class TaskCommentSerializer(serializers.ModelSerializer):
    """Serializer for TaskComment model."""
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'author', 'content', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class TaskAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for TaskAttachment model."""
    uploaded_by = UserSerializer(read_only=True)
    
    class Meta:
        model = TaskAttachment
        fields = ['id', 'task', 'file', 'filename', 'file_size', 'uploaded_by', 'uploaded_at']
        read_only_fields = ['uploaded_at', 'file_size']
    
    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        validated_data['filename'] = validated_data['file'].name
        validated_data['file_size'] = validated_data['file'].size
        return super().create(validated_data)


class WorkTaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model."""
    assigned_to = UserSerializer(read_only=True)
    assigned_by = UserSerializer(read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    is_overdue = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    is_high_priority = serializers.ReadOnlyField()
    
    class Meta:
        model = WorkTask
        fields = [
            'id', 'title', 'description', 'task_type', 'priority', 'status',
            'assigned_to', 'assigned_by', 'due_date', 'start_date', 'completed_date',
            'progress_percentage', 'customer', 'goal', 'store', 'estimated_hours',
            'actual_hours', 'notes', 'created_at', 'updated_at', 'comments',
            'attachments', 'is_overdue', 'days_remaining', 'is_high_priority'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_overdue', 'days_remaining', 'is_high_priority']


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tasks."""
    
    class Meta:
        model = WorkTask
        fields = [
            'title', 'description', 'task_type', 'priority', 'due_date',
            'assigned_to', 'customer', 'goal', 'store', 'estimated_hours', 'notes'
        ]
    
    def create(self, validated_data):
        validated_data['assigned_by'] = self.context['request'].user
        return super().create(validated_data)


class TaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tasks."""
    
    class Meta:
        model = WorkTask
        fields = [
            'title', 'description', 'task_type', 'priority', 'status',
            'assigned_to', 'due_date', 'progress_percentage', 'customer',
            'goal', 'store', 'estimated_hours', 'actual_hours', 'notes'
        ]


class TaskStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating task status."""
    
    class Meta:
        model = WorkTask
        fields = ['status', 'progress_percentage']
    
    def update(self, instance, validated_data):
        status = validated_data.get('status')
        progress = validated_data.get('progress_percentage', instance.progress_percentage)
        
        # Handle status transitions
        if status == WorkTask.Status.IN_PROGRESS and instance.status == WorkTask.Status.PENDING:
            instance.start_task()
        elif status == WorkTask.Status.COMPLETED:
            instance.complete_task()
        else:
            instance.status = status
            instance.progress_percentage = progress
            instance.save()
        
        return instance


class TaskProgressUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating task progress."""
    
    class Meta:
        model = WorkTask
        fields = ['progress_percentage']
    
    def update(self, instance, validated_data):
        progress = validated_data.get('progress_percentage')
        instance.update_progress(progress)
        return instance


class GoalProgressUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating goal progress."""
    
    class Meta:
        model = Goal
        fields = ['current_value']
    
    def update(self, instance, validated_data):
        new_value = validated_data.get('current_value')
        instance.update_progress(new_value)
        return instance


class TaskDashboardSerializer(serializers.ModelSerializer):
    """Serializer for task dashboard data."""
    assigned_to = UserSerializer(read_only=True)
    is_overdue = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = WorkTask
        fields = [
            'id', 'title', 'task_type', 'priority', 'status', 'assigned_to',
            'due_date', 'progress_percentage', 'is_overdue', 'days_remaining'
        ]


class GoalDashboardSerializer(serializers.ModelSerializer):
    """Serializer for goal dashboard data."""
    assigned_to = UserSerializer(read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = Goal
        fields = [
            'id', 'title', 'goal_type', 'period', 'target_value', 'current_value',
            'assigned_to', 'end_date', 'is_active', 'is_completed',
            'progress_percentage', 'is_overdue', 'days_remaining'
        ] 