from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AnnouncementViewSet, TeamMessageViewSet,
    AnnouncementReadViewSet, MessageReadViewSet
)

router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'messages', TeamMessageViewSet, basename='message')
router.register(r'announcement-reads', AnnouncementReadViewSet, basename='announcement-read')
router.register(r'message-reads', MessageReadViewSet, basename='message-read')

urlpatterns = [
    path('', include(router.urls)),
] 