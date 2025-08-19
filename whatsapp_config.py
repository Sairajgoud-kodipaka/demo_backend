"""
WhatsApp Business API Configuration
This file contains all WhatsApp-related configuration settings and validation.
"""

import os
from typing import Optional
from django.conf import settings

class WhatsAppConfig:
    """WhatsApp Business API Configuration Manager"""
    
    def __init__(self):
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN')
        self.business_account_id = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
        self.app_id = os.getenv('WHATSAPP_APP_ID')
        
        # Webhook URLs
        self.webhook_url = os.getenv('WHATSAPP_WEBHOOK_URL')
        self.webhook_verify_url = os.getenv('WHATSAPP_WEBHOOK_VERIFY_URL')
        
        # Development URLs
        self.dev_webhook_url = os.getenv('WHATSAPP_DEV_WEBHOOK_URL', 'http://localhost:8000/api/whatsapp/webhook/')
        self.dev_verify_url = os.getenv('WHATSAPP_DEV_VERIFY_URL', 'http://localhost:8000/api/whatsapp/verify/')
        
        # API Base URL
        self.api_base_url = "https://graph.facebook.com/v18.0"
        
    def is_configured(self) -> bool:
        """Check if all required WhatsApp configuration is present"""
        required_fields = [
            self.phone_number_id,
            self.access_token,
            self.verify_token
        ]
        return all(field is not None and field.strip() != '' for field in required_fields)
    
    def get_webhook_url(self, is_production: bool = False) -> str:
        """Get the appropriate webhook URL based on environment"""
        if is_production and self.webhook_url:
            return self.webhook_url
        return self.dev_webhook_url
    
    def get_verify_url(self, is_production: bool = False) -> str:
        """Get the appropriate verify URL based on environment"""
        if is_production and self.webhook_verify_url:
            return self.webhook_verify_url
        return self.dev_verify_url
    
    def get_api_url(self, endpoint: str) -> str:
        """Get full API URL for a given endpoint"""
        return f"{self.api_base_url}/{endpoint}"
    
    def get_headers(self) -> dict:
        """Get headers required for WhatsApp API requests"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate configuration and return errors if any"""
        errors = []
        
        if not self.phone_number_id:
            errors.append("WHATSAPP_PHONE_NUMBER_ID is not configured")
        
        if not self.access_token:
            errors.append("WHATSAPP_ACCESS_TOKEN is not configured")
        
        if not self.verify_token:
            errors.append("WHATSAPP_VERIFY_TOKEN is not configured")
        
        if not self.business_account_id:
            errors.append("WHATSAPP_BUSINESS_ACCOUNT_ID is not configured (optional but recommended)")
        
        return len(errors) == 0, errors

# Global WhatsApp configuration instance
whatsapp_config = WhatsAppConfig()

# WhatsApp API Endpoints
WHATSAPP_ENDPOINTS = {
    'send_message': f"{whatsapp_config.api_base_url}/{whatsapp_config.phone_number_id}/messages",
    'get_phone_number': f"{whatsapp_config.api_base_url}/{whatsapp_config.phone_number_id}",
    'get_business_profile': f"{whatsapp_config.api_base_url}/{whatsapp_config.phone_number_id}/whatsapp_business_profile",
    'get_templates': f"{whatsapp_config.api_base_url}/{whatsapp_config.phone_number_id}/message_templates",
    'create_template': f"{whatsapp_config.api_base_url}/{whatsapp_config.phone_number_id}/message_templates",
    'delete_template': f"{whatsapp_config.api_base_url}/",  # Will be appended with template_id
    'get_media': f"{whatsapp_config.api_base_url}/",  # Will be appended with media_id
    'upload_media': f"{whatsapp_config.api_base_url}/{whatsapp_config.phone_number_id}/media",
}

# WhatsApp Message Types
WHATSAPP_MESSAGE_TYPES = {
    'text': 'text',
    'image': 'image',
    'video': 'video',
    'audio': 'audio',
    'document': 'document',
    'location': 'location',
    'contact': 'contact',
    'sticker': 'sticker',
    'template': 'template',
    'interactive': 'interactive',
    'reaction': 'reaction',
}

# WhatsApp Template Categories
WHATSAPP_TEMPLATE_CATEGORIES = [
    'ACCOUNT_UPDATE',
    'ALERT_UPDATE',
    'APPOINTMENT_UPDATE',
    'AUTO_REPLY',
    'ISSUE_RESOLUTION',
    'MARKETING',
    'PAYMENT_UPDATE',
    'PERSONAL_FINANCE_UPDATE',
    'RESERVATION_UPDATE',
    'SHIPPING_UPDATE',
    'TICKET_UPDATE',
    'TRANSPORTATION_UPDATE',
]

# WhatsApp Template Languages
WHATSAPP_TEMPLATE_LANGUAGES = [
    'af', 'sq', 'ar', 'az', 'bn', 'bg', 'ca', 'zh_CN', 'zh_HK', 'zh_TW',
    'hr', 'cs', 'da', 'nl', 'en', 'en_GB', 'en_US', 'et', 'fil', 'fi',
    'fr', 'de', 'el', 'gu', 'he', 'hi', 'hu', 'id', 'ga', 'it', 'ja',
    'kn', 'kk', 'ko', 'lo', 'lv', 'lt', 'mk', 'ms', 'ml', 'mr', 'nb',
    'fa', 'pl', 'pt_BR', 'pt_PT', 'pa', 'ro', 'ru', 'sr', 'sk', 'sl',
    'es', 'es_AR', 'es_ES', 'es_MX', 'sw', 'sv', 'ta', 'te', 'th', 'tr',
    'uk', 'ur', 'uz', 'vi', 'zu'
]

# WhatsApp Webhook Event Types
WHATSAPP_WEBHOOK_EVENTS = {
    'message': 'messages',
    'message_status': 'message_status',
    'message_template_status': 'message_template_status',
    'business_account_update': 'business_account_update',
    'phone_number_update': 'phone_number_update',
    'account_update': 'account_update',
    'account_alerts': 'account_alerts',
    'message_reaction': 'message_reaction',
    'message_revoked': 'message_revoked',
    'message_edited': 'message_edited',
}

# WhatsApp Message Status Types
WHATSAPP_MESSAGE_STATUS = {
    'sent': 'sent',
    'delivered': 'delivered',
    'read': 'read',
    'failed': 'failed',
    'deleted': 'deleted',
}

# WhatsApp Template Status Types
WHATSAPP_TEMPLATE_STATUS = {
    'approved': 'APPROVED',
    'pending': 'PENDING',
    'rejected': 'REJECTED',
    'disabled': 'DISABLED',
    'in_appeal': 'IN_APPEAL',
}

# Rate Limiting Configuration
WHATSAPP_RATE_LIMITS = {
    'messages_per_second': 5,
    'messages_per_minute': 300,
    'messages_per_hour': 1000,
    'messages_per_day': 10000,
    'templates_per_day': 100,
    'media_upload_size_mb': 16,
}

# Error Codes and Messages
WHATSAPP_ERROR_CODES = {
    '100': 'Invalid parameter',
    '102': 'API rate limit exceeded',
    '103': 'Invalid phone number',
    '104': 'Invalid message template',
    '105': 'Message template not found',
    '106': 'Message template rejected',
    '107': 'Message template disabled',
    '108': 'Message template expired',
    '109': 'Message template language not supported',
    '110': 'Message template category not supported',
    '111': 'Message template format not supported',
    '112': 'Message template parameter missing',
    '113': 'Message template parameter invalid',
    '114': 'Message template parameter too long',
    '115': 'Message template parameter too short',
    '116': 'Message template parameter count exceeded',
    '117': 'Message template parameter count insufficient',
    '118': 'Message template parameter type not supported',
    '119': 'Message template parameter value not supported',
    '120': 'Message template parameter value too long',
    '121': 'Message template parameter value too short',
    '122': 'Message template parameter value count exceeded',
    '123': 'Message template parameter value count insufficient',
    '124': 'Message template parameter value type not supported',
    '125': 'Message template parameter value format not supported',
    '126': 'Message template parameter value language not supported',
    '127': 'Message template parameter value category not supported',
    '128': 'Message template parameter value format not supported',
    '129': 'Message template parameter value language not supported',
    '130': 'Message template parameter value category not supported',
} 