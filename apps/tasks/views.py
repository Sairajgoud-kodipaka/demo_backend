from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Goal, WorkTask, TaskComment, TaskAttachment
from .serializers import (
    GoalSerializer, GoalCreateSerializer, GoalUpdateSerializer, GoalProgressUpdateSerializer,
    WorkTaskSerializer, TaskCreateSerializer, TaskUpdateSerializer, TaskStatusUpdateSerializer,
    TaskProgressUpdateSerializer, TaskCommentSerializer, TaskAttachmentSerializer,
    TaskDashboardSerializer, GoalDashboardSerializer
)
from apps.users.permissions import IsManagerOrHigher, IsBusinessAdminOrHigher


class GoalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing goals.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['goal_type', 'period', 'is_active', 'is_completed', 'assigned_to', 'store']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'end_date', 'target_value', 'current_value']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        
        # Platform admins can see all goals
        if user.is_platform_admin:
            return Goal.objects.all()
        
        # Business admins can see goals in their tenant
        if user.is_business_admin:
            return Goal.objects.filter(store__tenant=user.tenant)
        
        # Managers can see goals in their store
        if user.is_manager:
            return Goal.objects.filter(store=user.store)
        
        # Regular users can only see their own goals
        return Goal.objects.filter(assigned_to=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return GoalCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return GoalUpdateSerializer
        elif self.action == 'update_progress':
            return GoalProgressUpdateSerializer
        return GoalSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Allow all authenticated users to create goals, not just managers
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update goal progress."""
        goal = self.get_object()
        serializer = self.get_serializer(goal, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(GoalSerializer(goal).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get goals for dashboard view."""
        queryset = self.get_queryset()
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True, is_completed=False)
        elif status_filter == 'completed':
            queryset = queryset.filter(is_completed=True)
        elif status_filter == 'overdue':
            queryset = queryset.filter(end_date__lt=timezone.now().date(), is_completed=False)
        
        serializer = GoalDashboardSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get goal statistics."""
        queryset = self.get_queryset()
        
        total_goals = queryset.count()
        active_goals = queryset.filter(is_active=True, is_completed=False).count()
        completed_goals = queryset.filter(is_completed=True).count()
        overdue_goals = queryset.filter(end_date__lt=timezone.now().date(), is_completed=False).count()
        
        # Average progress for active goals
        active_goals_data = queryset.filter(is_active=True, is_completed=False)
        avg_progress = active_goals_data.aggregate(avg_progress=Avg('current_value'))['avg_progress'] or 0
        
        return Response({
            'total_goals': total_goals,
            'active_goals': active_goals,
            'completed_goals': completed_goals,
            'overdue_goals': overdue_goals,
            'average_progress': float(avg_progress),
            'completion_rate': (completed_goals / total_goals * 100) if total_goals > 0 else 0
        })


class WorkTaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tasks.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task_type', 'priority', 'status', 'assigned_to', 'store', 'goal']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'due_date', 'priority', 'progress_percentage']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        
        # Platform admins can see all tasks
        if user.is_platform_admin:
            return WorkTask.objects.all()
        
        # Business admins can see tasks in their tenant
        if user.is_business_admin:
            return WorkTask.objects.filter(store__tenant=user.tenant)
        
        # Managers can see tasks in their store
        if user.is_manager:
            return WorkTask.objects.filter(store=user.store)
        
        # Regular users can only see their own tasks
        return WorkTask.objects.filter(assigned_to=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return TaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskUpdateSerializer
        elif self.action == 'update_status':
            return TaskStatusUpdateSerializer
        elif self.action == 'update_progress':
            return TaskProgressUpdateSerializer
        return WorkTaskSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Allow all authenticated users to create tasks, not just managers
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update task status."""
        task = self.get_object()
        serializer = self.get_serializer(task, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(WorkTaskSerializer(task).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update task progress."""
        task = self.get_object()
        serializer = self.get_serializer(task, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(WorkTaskSerializer(task).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def start_task(self, request, pk=None):
        """Start a task."""
        task = self.get_object()
        task.start_task()
        return Response(WorkTaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def complete_task(self, request, pk=None):
        """Complete a task."""
        task = self.get_object()
        task.complete_task()
        return Response(WorkTaskSerializer(task).data)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get tasks for dashboard view."""
        queryset = self.get_queryset()
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by priority if provided
        priority_filter = request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        # Filter overdue tasks
        overdue_filter = request.query_params.get('overdue')
        if overdue_filter == 'true':
            queryset = queryset.filter(due_date__lt=timezone.now(), status__in=['pending', 'in_progress'])
        
        serializer = TaskDashboardSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get task statistics."""
        queryset = self.get_queryset()
        
        total_tasks = queryset.count()
        pending_tasks = queryset.filter(status='pending').count()
        in_progress_tasks = queryset.filter(status='in_progress').count()
        completed_tasks = queryset.filter(status='completed').count()
        overdue_tasks = queryset.filter(due_date__lt=timezone.now(), status__in=['pending', 'in_progress']).count()
        
        # Priority breakdown
        high_priority_tasks = queryset.filter(priority__in=['high', 'urgent']).count()
        urgent_tasks = queryset.filter(priority='urgent').count()
        
        # Average progress for in-progress tasks
        in_progress_data = queryset.filter(status='in_progress')
        avg_progress = in_progress_data.aggregate(avg_progress=Avg('progress_percentage'))['avg_progress'] or 0
        
        return Response({
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'high_priority_tasks': high_priority_tasks,
            'urgent_tasks': urgent_tasks,
            'average_progress': float(avg_progress),
            'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        })

    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """Get current user's tasks."""
        queryset = self.get_queryset().filter(assigned_to=request.user)
        serializer = TaskDashboardSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def due_soon(self, request):
        """Get tasks due within the next 7 days."""
        seven_days_from_now = timezone.now() + timedelta(days=7)
        queryset = self.get_queryset().filter(
            due_date__lte=seven_days_from_now,
            status__in=['pending', 'in_progress']
        )
        serializer = TaskDashboardSerializer(queryset, many=True)
        return Response(serializer.data)


class TaskCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing task comments.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TaskCommentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        
        # Platform admins can see all comments
        if user.is_platform_admin:
            return TaskComment.objects.all()
        
        # Business admins can see comments for tasks in their tenant
        if user.is_business_admin:
            return TaskComment.objects.filter(task__store__tenant=user.tenant)
        
        # Managers can see comments for tasks in their store
        if user.is_manager:
            return TaskComment.objects.filter(task__store=user.store)
        
        # Regular users can only see comments for their own tasks
        return TaskComment.objects.filter(task__assigned_to=user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class TaskAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing task attachments.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TaskAttachmentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task']
    ordering = ['-uploaded_at']

    def get_queryset(self):
        user = self.request.user
        
        # Platform admins can see all attachments
        if user.is_platform_admin:
            return TaskAttachment.objects.all()
        
        # Business admins can see attachments for tasks in their tenant
        if user.is_business_admin:
            return TaskAttachment.objects.filter(task__store__tenant=user.tenant)
        
        # Managers can see attachments for tasks in their store
        if user.is_manager:
            return TaskAttachment.objects.filter(task__store=user.store)
        
        # Regular users can only see attachments for their own tasks
        return TaskAttachment.objects.filter(task__assigned_to=user)

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user) 