from django.apps import AppConfig


class WhatsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.whatsapp'
    verbose_name = 'WhatsApp Business'
    
    def ready(self):
        """Initialize WhatsApp app when Django starts"""
        try:
            # Import signals if they exist
            import apps.whatsapp.signals
        except ImportError:
            pass
