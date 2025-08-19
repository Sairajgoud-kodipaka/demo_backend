from django.urls import path
from . import views

app_name = 'marketing'

urlpatterns = [
    # Campaign Management
    path('campaigns/', views.MarketingCampaignListCreateView.as_view(), name='campaign-list-create'),
    path('campaigns/<uuid:id>/', views.MarketingCampaignDetailView.as_view(), name='campaign-detail'),
    
    # Message Templates
    path('templates/', views.MessageTemplateListCreateView.as_view(), name='template-list-create'),
    path('templates/<int:pk>/', views.MessageTemplateDetailView.as_view(), name='template-detail'),
    
    # E-commerce Platforms
    path('platforms/', views.EcommercePlatformListCreateView.as_view(), name='platform-list-create'),
    path('platforms/<int:pk>/', views.EcommercePlatformDetailView.as_view(), name='platform-detail'),
    
    # Customer Segments
    path('segments/', views.CustomerSegmentListCreateView.as_view(), name='segment-list-create'),
    path('segments/<int:pk>/', views.CustomerSegmentDetailView.as_view(), name='segment-detail'),
    
    # Dashboard and Analytics
    path('dashboard/', views.MarketingDashboardView.as_view(), name='dashboard'),
    path('campaign-metrics/', views.CampaignMetricsView.as_view(), name='campaign-metrics'),
    path('segment-overview/', views.SegmentOverviewView.as_view(), name='segment-overview'),
    path('realtime-analytics/', views.RealTimeAnalyticsView.as_view(), name='realtime-analytics'),
    path('ecommerce-summary/', views.EcommerceSummaryView.as_view(), name='ecommerce-summary'),
    path('whatsapp-metrics/', views.WhatsAppMetricsView.as_view(), name='whatsapp-metrics'),
    
    # List Views for Components
    path('campaign-list/', views.CampaignListView.as_view(), name='campaign-list'),
    path('template-list/', views.TemplateListView.as_view(), name='template-list'),
    path('platform-list/', views.PlatformListView.as_view(), name='platform-list'),
] 