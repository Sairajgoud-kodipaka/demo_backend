from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SupportTicketViewSet, TicketMessageViewSet, 
    SupportNotificationViewSet, SupportSettingsViewSet
)

router = DefaultRouter()
router.register(r'tickets', SupportTicketViewSet, basename='support-ticket')
router.register(r'messages', TicketMessageViewSet, basename='ticket-message')
router.register(r'notifications', SupportNotificationViewSet, basename='support-notification')
router.register(r'settings', SupportSettingsViewSet, basename='support-settings')

urlpatterns = [
    path('', include(router.urls)),
] 