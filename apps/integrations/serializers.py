from rest_framework import serializers
from .models import Integration, WhatsAppIntegration, EcommerceIntegration, IntegrationLog

class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = '__all__'

class WhatsAppIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppIntegration
        fields = '__all__'

class EcommerceIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcommerceIntegration
        fields = '__all__'

class IntegrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationLog
        fields = '__all__'
