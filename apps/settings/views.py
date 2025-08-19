from rest_framework import viewsets
from .models import BusinessSetting, Tag, NotificationTemplate, BrandingSetting, LegalSetting
from .serializers import (
    BusinessSettingSerializer, TagSerializer, NotificationTemplateSerializer, BrandingSettingSerializer, LegalSettingSerializer
)

class BusinessSettingViewSet(viewsets.ModelViewSet):
    queryset = BusinessSetting.objects.all()
    serializer_class = BusinessSettingSerializer

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer

class BrandingSettingViewSet(viewsets.ModelViewSet):
    queryset = BrandingSetting.objects.all()
    serializer_class = BrandingSettingSerializer

class LegalSettingViewSet(viewsets.ModelViewSet):
    queryset = LegalSetting.objects.all()
    serializer_class = LegalSettingSerializer 