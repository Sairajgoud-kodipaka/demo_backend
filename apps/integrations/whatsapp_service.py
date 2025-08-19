import requests
import json
from typing import Optional, Dict, Any
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class WhatsAppService:
    """
    WhatsApp service using WAHA (WhatsApp HTTP API)
    Documentation: https://waha.devlike.pro/
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'WAHA_BASE_URL', 'http://localhost:3000')
        self.session = getattr(settings, 'WAHA_SESSION', 'default')
        self.api_key = getattr(settings, 'WAHA_API_KEY', None)
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for WAHA API requests"""
        headers = {
            'Content-Type': 'application/json',
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for WhatsApp (add @c.us suffix)"""
        # Remove any non-numeric characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # Add country code if not present (assuming India +91)
        if not phone.startswith('91') and len(phone) == 10:
            phone = '91' + phone
            
        return f"{phone}@c.us"
    
    def send_text_message(self, phone: str, message: str) -> bool:
        """
        Send a text message via WhatsApp
        
        Args:
            phone: Phone number (will be formatted automatically)
            message: Text message to send
            
        Returns:
            bool: True if message sent successfully
        """
        try:
            chat_id = self._format_phone_number(phone)
            
            payload = {
                "session": self.session,
                "chatId": chat_id,
                "text": message
            }
            
            response = requests.post(
                f"{self.base_url}/api/sendText",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            logger.info(f"WAHA Response - Status: {response.status_code}, Content: {response.text}")
            
            # WAHA typically returns 200 or 201 for successful sends
            if response.status_code in [200, 201]:
                logger.info(f"WhatsApp message sent successfully to {phone}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message to {phone}: {str(e)}")
            return False
    
    def send_image_message(self, phone: str, image_url: str, caption: Optional[str] = None) -> bool:
        """
        Send an image message via WhatsApp
        
        Args:
            phone: Phone number
            image_url: URL of the image to send
            caption: Optional caption for the image
            
        Returns:
            bool: True if message sent successfully
        """
        try:
            chat_id = self._format_phone_number(phone)
            
            payload = {
                "session": self.session,
                "chatId": chat_id,
                "file": {
                    "url": image_url
                }
            }
            
            if caption:
                payload["file"]["caption"] = caption
            
            response = requests.post(
                f"{self.base_url}/api/sendImage",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"WhatsApp image sent successfully to {phone}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp image: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp image to {phone}: {str(e)}")
            return False
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get the status of the WhatsApp session"""
        try:
            response = requests.get(
                f"{self.base_url}/api/sessions",
                headers=self._get_headers(),
                timeout=10
            )
            
            logger.info(f"WAHA sessions response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                sessions = response.json()
                for session in sessions:
                    if session.get('name') == self.session:
                        logger.info(f"Found session: {session}")
                        
                        # If session is working, get the user profile information
                        if session.get('status') == 'WORKING':
                            try:
                                # Try different profile endpoints
                                profile_endpoints = [
                                    f"{self.base_url}/api/{self.session}/profile",
                                    f"{self.base_url}/api/{self.session}/me",
                                    f"{self.base_url}/api/{self.session}/user"
                                ]
                                
                                profile_data = None
                                for endpoint in profile_endpoints:
                                    try:
                                        logger.info(f"Trying profile endpoint: {endpoint}")
                                        profile_response = requests.get(
                                            endpoint,
                                            headers=self._get_headers(),
                                            timeout=10
                                        )
                                        
                                        if profile_response.status_code == 200:
                                            profile_data = profile_response.json()
                                            logger.info(f"Profile data from {endpoint}: {profile_data}")
                                            break
                                        else:
                                            logger.warning(f"Profile endpoint {endpoint} returned {profile_response.status_code}")
                                    except Exception as endpoint_error:
                                        logger.warning(f"Error with endpoint {endpoint}: {str(endpoint_error)}")
                                        continue
                                
                                if profile_data:
                                    # Add the user profile to the session data
                                    session['me'] = {
                                        'name': profile_data.get('name', profile_data.get('displayName', 'Unknown')),
                                        'number': profile_data.get('id', profile_data.get('phone', 'Unknown'))
                                    }
                                else:
                                    logger.warning("Could not fetch profile from any endpoint")
                                    # Add default me object if profile fetch fails
                                    session['me'] = {
                                        'name': 'Connected',
                                        'number': 'Active Session'
                                    }
                            except Exception as profile_error:
                                logger.warning(f"Error getting profile: {str(profile_error)}")
                                # Add default me object if profile fetch fails
                                session['me'] = {
                                    'name': 'Connected',
                                    'number': 'Active Session'
                                }
                        
                        return session
                return {'status': 'NOT_FOUND'}
            else:
                return {'status': 'ERROR', 'message': response.text}
                
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            return {'status': 'ERROR', 'message': str(e)}
    
    def start_session(self) -> bool:
        """Start a new WhatsApp session"""
        try:
            payload = {
                "name": self.session,
                "config": {
                    "webhooks": [
                        {
                            "url": f"{settings.SITE_URL}/api/webhooks/whatsapp/",
                            "events": ["message", "session.status"]
                        }
                    ]
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/sessions",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            return response.status_code in [200, 201]
            
        except Exception as e:
            logger.error(f"Error starting session: {str(e)}")
            return False

# Notification templates for jewelry business
class JewelryWhatsAppTemplates:
    """Pre-defined WhatsApp message templates for jewelry business"""
    
    @staticmethod
    def appointment_reminder(customer_name: str, appointment_date: str, appointment_time: str, store_name: str) -> str:
        return f"""
🏅 *{store_name}* - Appointment Reminder

Hello {customer_name}! 👋

This is a friendly reminder about your jewelry consultation:

📅 *Date:* {appointment_date}
🕐 *Time:* {appointment_time}
📍 *Location:* {store_name}

We're excited to help you find the perfect jewelry! ✨

If you need to reschedule, please let us know.

Thank you! 💎
        """.strip()
    
    @staticmethod
    def order_ready(customer_name: str, order_number: str, product_name: str, store_name: str) -> str:
        return f"""
🎉 *Great News {customer_name}!*

Your custom jewelry is ready for pickup! ✨

📋 *Order #:* {order_number}
💎 *Item:* {product_name}
📍 *Pickup Location:* {store_name}

Please bring a valid ID when collecting your order.

Store Hours: 10 AM - 8 PM
Contact us for any queries.

Thank you for choosing us! 🙏
        """.strip()
    
    @staticmethod
    def payment_reminder(customer_name: str, amount: str, due_date: str, order_number: str) -> str:
        return f"""
💳 *Payment Reminder*

Hello {customer_name},

This is a gentle reminder for your pending payment:

📋 *Order #:* {order_number}
💰 *Amount Due:* ₹{amount}
📅 *Due Date:* {due_date}

You can pay via:
• Cash at store
• Online transfer
• UPI

Contact us for payment assistance.

Thank you! 🙏
        """.strip()
    
    @staticmethod
    def new_collection_launch(customer_name: str, collection_name: str, discount: str, store_name: str) -> str:
        return f"""
✨ *Exciting News {customer_name}!*

We've launched our new *{collection_name}* collection! 💎

🎊 *Special Launch Offer:*
🔥 {discount}% OFF on all items
⏰ Limited time only!

Visit {store_name} to explore our stunning new designs.

Don't miss out on these exclusive pieces! 👑

Visit us today! ✨
        """.strip()
    
    @staticmethod
    def follow_up_message(customer_name: str, product_interest: str, salesperson_name: str) -> str:
        return f"""
Hello {customer_name}! 👋

I hope you're doing well. This is {salesperson_name} from our jewelry store.

I wanted to follow up on your interest in *{product_interest}*.

Do you have any questions about:
• Product specifications 💎
• Pricing and offers 💰
• Customization options ✨
• Visit scheduling 📅

Feel free to reach out anytime!

Best regards,
{salesperson_name} 🙏
        """.strip()

# Usage examples for your CRM:
"""
# Initialize service
whatsapp = WhatsAppService()

# Send appointment reminder
whatsapp.send_text_message(
    phone="+919876543210",
    message=JewelryWhatsAppTemplates.appointment_reminder(
        customer_name="Priya Sharma",
        appointment_date="Tomorrow",
        appointment_time="3:00 PM", 
        store_name="Mandeep Jewellers"
    )
)

# Send order ready notification
whatsapp.send_text_message(
    phone="+919876543210",
    message=JewelryWhatsAppTemplates.order_ready(
        customer_name="Rahul Kumar",
        order_number="ORD-001",
        product_name="Gold Wedding Ring",
        store_name="Mandeep Jewellers"
    )
)

# Send new collection with image
whatsapp.send_image_message(
    phone="+919876543210",
    image_url="https://yourstore.com/collections/new-gold-necklaces.jpg",
    caption=JewelryWhatsAppTemplates.new_collection_launch(
        customer_name="Anjali Patel",
        collection_name="Royal Gold",
        discount="20",
        store_name="Mandeep Jewellers"
    )
)
"""

