from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.integrations.whatsapp_service import WhatsAppService, JewelryWhatsAppTemplates
from apps.clients.models import Client, Appointment
from apps.sales.models import Sale


class Command(BaseCommand):
    help = 'Send WhatsApp notifications for appointments, orders, etc.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            help='Type of notification: appointments, orders, follow_ups',
            choices=['appointments', 'orders', 'follow_ups', 'all'],
            default='all'
        )

    def handle(self, *args, **options):
        whatsapp = WhatsAppService()
        notification_type = options['type']

        if notification_type in ['appointments', 'all']:
            self.send_appointment_reminders(whatsapp)

        if notification_type in ['orders', 'all']:
            self.send_order_notifications(whatsapp)

        if notification_type in ['follow_ups', 'all']:
            self.send_follow_up_messages(whatsapp)

    def send_appointment_reminders(self, whatsapp):
        """Send reminders for appointments tomorrow"""
        tomorrow = timezone.now().date() + timedelta(days=1)
        
        appointments = Appointment.objects.filter(
            date=tomorrow,
            status='confirmed',
            is_deleted=False
        )

        sent_count = 0
        for appointment in appointments:
            if appointment.client.phone:
                message = JewelryWhatsAppTemplates.appointment_reminder(
                    customer_name=appointment.client.first_name,
                    appointment_date=appointment.date.strftime('%B %d, %Y'),
                    appointment_time=appointment.time.strftime('%I:%M %p'),
                    store_name=appointment.client.store.name if appointment.client.store else "Our Store"
                )
                
                if whatsapp.send_text_message(appointment.client.phone, message):
                    sent_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Sent appointment reminder to {appointment.client.first_name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'Sent {sent_count} appointment reminders')
        )

    def send_order_notifications(self, whatsapp):
        """Send notifications for ready orders"""
        ready_orders = Sale.objects.filter(
            status='ready_for_pickup',
            # Add your logic for orders ready for pickup
        )

        sent_count = 0
        for order in ready_orders:
            if order.client.phone:
                message = JewelryWhatsAppTemplates.order_ready(
                    customer_name=order.client.first_name,
                    order_number=order.order_number,
                    product_name="Your Order",  # You can enhance this
                    store_name=order.client.store.name if order.client.store else "Our Store"
                )
                
                if whatsapp.send_text_message(order.client.phone, message):
                    sent_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Sent order notification to {order.client.first_name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'Sent {sent_count} order notifications')
        )

    def send_follow_up_messages(self, whatsapp):
        """Send follow-up messages to prospects"""
        # Get clients who haven't been contacted in a week
        one_week_ago = timezone.now() - timedelta(days=7)
        
        prospects = Client.objects.filter(
            customer_type='prospect',
            created_at__lte=one_week_ago,
            # Add logic for last contact date
        )

        sent_count = 0
        for client in prospects:
            if client.phone:
                message = JewelryWhatsAppTemplates.follow_up_message(
                    customer_name=client.first_name,
                    product_interest=client.customer_interests or "our jewelry collection",
                    salesperson_name=client.assigned_to.first_name if client.assigned_to else "Our Team"
                )
                
                if whatsapp.send_text_message(client.phone, message):
                    sent_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Sent follow-up to {client.first_name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'Sent {sent_count} follow-up messages')
        )

