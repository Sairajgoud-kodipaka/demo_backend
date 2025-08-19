from rest_framework import serializers
from .models import AnalyticsEvent, BusinessMetrics, DashboardWidget, Report

class AnalyticsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsEvent
        fields = '__all__'

class BusinessMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessMetrics
        fields = '__all__'

class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'
