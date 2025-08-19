from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import Q
from apps.users.middleware import ScopedVisibilityMiddleware
from .models import Notification, NotificationSettings
from .serializers import (
    NotificationSerializer, NotificationSettingsSerializer,
    NotificationCreateSerializer, NotificationUpdateSerializer
)


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [AllowAny]  # Temporarily disable authentication for testing
    
    def get_queryset(self):
        # Temporarily return all notifications for testing
        return Notification.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NotificationUpdateSerializer
        return NotificationSerializer
    
    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            tenant=self.request.user.tenant
        )
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'success'})
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        queryset = self.get_queryset()
        queryset.filter(status='unread').update(
            status='read',
            read_at=timezone.now()
        )
        return Response({'status': 'success'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        queryset = self.get_queryset()
        count = queryset.filter(status='unread').count()
        return Response({'count': count})
    
    @action(detail=False, methods=['get'])
    def test_endpoint(self, request):
        """Test endpoint to debug authentication issues"""
        return Response({
            'message': 'Test endpoint working',
            'user': str(request.user) if request.user.is_authenticated else 'Anonymous',
            'auth_header': request.headers.get('Authorization', 'No auth header'),
            'total_notifications': Notification.objects.count()
        })


class NotificationSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NotificationSettings.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            tenant=self.request.user.tenant
        )
    
    @action(detail=False, methods=['get'])
    def my_settings(self, request):
        settings, created = NotificationSettings.objects.get_or_create(
            user=request.user,
            defaults={
                'tenant': request.user.tenant,
                'email_enabled': True,
                'push_enabled': True,
                'in_app_enabled': True,
                'email_types': ['appointment_reminder', 'deal_update', 'inventory_alert'],
                'push_types': ['appointment_reminder', 'deal_update', 'inventory_alert'],
                'in_app_types': ['appointment_reminder', 'deal_update', 'inventory_alert'],
                'appointment_reminders': True,
                'deal_updates': True,
                'order_notifications': True,
                'inventory_alerts': True,
                'task_reminders': True,
                'announcements': True,
                'escalations': True,
                'marketing_updates': False,
            }
        )
        serializer = self.get_serializer(settings)
        return Response(serializer.data)


 