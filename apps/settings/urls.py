from rest_framework.routers import DefaultRouter
from .views import (
    BusinessSettingViewSet, TagViewSet, NotificationTemplateViewSet, BrandingSettingViewSet, LegalSettingViewSet
)

router = DefaultRouter()
router.register(r'business', BusinessSettingViewSet, basename='businesssetting')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'notifications', NotificationTemplateViewSet, basename='notificationtemplate')
router.register(r'branding', BrandingSettingViewSet, basename='brandingsetting')
router.register(r'legal', LegalSettingViewSet, basename='legalsetting')

urlpatterns = router.urls 