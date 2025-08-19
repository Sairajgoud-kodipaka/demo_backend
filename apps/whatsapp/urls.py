from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'whatsapp'

# API Router for viewsets
router = DefaultRouter()
router.register(r'sessions', views.WhatsAppSessionListView, basename='session')
router.register(r'contacts', views.WhatsAppContactListView, basename='contact')
router.register(r'messages', views.WhatsAppMessageListView, basename='message')
router.register(r'bots', views.WhatsAppBotListView, basename='bot')
router.register(r'triggers', views.WhatsAppBotTriggerListView, basename='trigger')
router.register(r'campaigns', views.WhatsAppCampaignListView, basename='campaign')
router.register(r'team-members', views.WhatsAppTeamMemberListView, basename='team-member')
router.register(r'conversations', views.WhatsAppConversationListView, basename='conversation')

urlpatterns = [
    # Include router URLs
    path('api/', include(router.urls)),
    
    # Session Management
    path('api/sessions/<uuid:id>/', views.WhatsAppSessionDetailView.as_view(), name='session-detail'),
    path('api/sessions/<str:session_id>/status/', views.WhatsAppSessionStatusView.as_view(), name='session-status'),
    
    # Contact Management
    path('api/contacts/<uuid:id>/', views.WhatsAppContactDetailView.as_view(), name='contact-detail'),
    
    # Message Management
    path('api/messages/send/', views.SendWhatsAppMessageView.as_view(), name='send-message'),
    
    # Bot Management
    path('api/bots/<uuid:id>/', views.WhatsAppBotDetailView.as_view(), name='bot-detail'),
    
    # Campaign Management
    path('api/campaigns/<uuid:id>/', views.WhatsAppCampaignDetailView.as_view(), name='campaign-detail'),
    path('api/campaigns/<uuid:campaign_id>/send/', views.SendCampaignView.as_view(), name='send-campaign'),
    
    # Team Management
    path('api/team-members/<uuid:id>/', views.WhatsAppTeamMemberDetailView.as_view(), name='team-member-detail'),
    path('api/team-members/<uuid:team_member_id>/performance/', views.TeamPerformanceView.as_view(), name='team-performance'),
    path('api/conversations/assign/', views.AssignConversationView.as_view(), name='assign-conversation'),
    
    # Conversation Management
    path('api/conversations/<uuid:id>/', views.WhatsAppConversationDetailView.as_view(), name='conversation-detail'),
    
    # Analytics and Dashboard
    path('api/analytics/', views.WhatsAppAnalyticsView.as_view(), name='analytics'),
    path('api/dashboard/', views.WhatsAppDashboardView.as_view(), name='dashboard'),
    
    # Webhook endpoints
    path('webhook/<str:session_name>/', views.whatsapp_webhook, name='webhook'),
    path('webhook/test/', views.test_webhook, name='test-webhook'),
    
    # Legacy endpoints for backward compatibility
    path('api/send/', views.SendWhatsAppMessageView.as_view(), name='legacy-send'),
    path('api/status/', views.WhatsAppSessionStatusView.as_view(), name='legacy-status'),
]
