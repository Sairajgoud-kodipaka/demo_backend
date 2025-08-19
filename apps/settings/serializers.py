from rest_framework import serializers
from .models import BusinessSetting, Tag, NotificationTemplate, BrandingSetting, LegalSetting

class BusinessSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSetting
        fields = '__all__'

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'

class BrandingSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandingSetting
        fields = '__all__'

class LegalSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalSetting
        fields = '__all__' 