from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerVisitViewSet, AssignmentViewSet, CallLogViewSet, FollowUpViewSet,
    CustomerProfileViewSet, NotificationViewSet, AnalyticsViewSet
)

router = DefaultRouter()
router.register(r'customer-visits', CustomerVisitViewSet)
router.register(r'assignments', AssignmentViewSet)
router.register(r'call-logs', CallLogViewSet)
router.register(r'followups', FollowUpViewSet)
router.register(r'customer-profiles', CustomerProfileViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'analytics', AnalyticsViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 