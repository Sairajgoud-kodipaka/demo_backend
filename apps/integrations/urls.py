from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    # WhatsApp Integration
    path('whatsapp/status/', views.WhatsAppStatusView.as_view(), name='whatsapp_status'),
    path('whatsapp/session/start/', views.WhatsAppSessionView.as_view(), name='whatsapp_start_session'),
    path('whatsapp/send/', views.SendWhatsAppMessageView.as_view(), name='whatsapp_send_message'),
    path('whatsapp/bulk/', views.SendBulkWhatsAppView.as_view(), name='whatsapp_bulk_send'),
    path('whatsapp/templates/', views.WhatsAppTemplatesView.as_view(), name='whatsapp_templates'),
    
    # Webhook endpoint
    path('webhooks/whatsapp/', views.whatsapp_webhook, name='whatsapp_webhook'),
]