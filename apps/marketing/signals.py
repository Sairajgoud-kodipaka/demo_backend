from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import (
    MarketingCampaign, MessageTemplate, EcommercePlatform, 
    CustomerSegment, MarketingEvent
)


@receiver(post_save, sender=MarketingCampaign)
def create_campaign_event(sender, instance, created, **kwargs):
    """Create marketing event when campaign is created or updated"""
    if created:
        MarketingEvent.objects.create(
            event_type=MarketingEvent.EventType.CAMPAIGN_LAUNCHED,
            title=f"Campaign '{instance.name}' created",
            description=f"New {instance.get_campaign_type_display()} campaign created",
            campaign=instance,
            tenant=instance.tenant,
            store=instance.store
        )
    elif instance.status == 'completed':
        MarketingEvent.objects.create(
            event_type=MarketingEvent.EventType.CAMPAIGN_COMPLETED,
            title=f"Campaign '{instance.name}' completed",
            description=f"Campaign completed with {instance.conversions} conversions",
            campaign=instance,
            tenant=instance.tenant,
            store=instance.store
        )


@receiver(post_save, sender=MessageTemplate)
def create_template_event(sender, instance, created, **kwargs):
    """Create marketing event when template is created"""
    if created:
        MarketingEvent.objects.create(
            event_type=MarketingEvent.EventType.TEMPLATE_CREATED,
            title=f"Template '{instance.name}' created",
            description=f"New {instance.get_template_type_display()} template created",
            template=instance,
            tenant=instance.tenant,
            store=instance.store
        )


@receiver(post_save, sender=EcommercePlatform)
def create_platform_event(sender, instance, created, **kwargs):
    """Create marketing event when platform is connected"""
    if created and instance.status == 'connected':
        MarketingEvent.objects.create(
            event_type=MarketingEvent.EventType.PLATFORM_CONNECTED,
            title=f"Platform '{instance.name}' connected",
            description=f"{instance.get_platform_type_display()} platform connected successfully",
            platform=instance,
            tenant=instance.tenant,
            store=instance.store
        )


@receiver(post_save, sender=CustomerSegment)
def create_segment_event(sender, instance, created, **kwargs):
    """Create marketing event when segment is created"""
    if created:
        MarketingEvent.objects.create(
            event_type=MarketingEvent.EventType.SEGMENT_CREATED,
            title=f"Segment '{instance.name}' created",
            description=f"New customer segment with {instance.customer_count} customers",
            segment=instance,
            tenant=instance.tenant,
            store=instance.store
        )


@receiver(post_save, sender=MarketingCampaign)
def track_high_conversion(sender, instance, **kwargs):
    """Track high conversion campaigns"""
    if instance.conversion_rate > 5.0:  # High conversion threshold
        MarketingEvent.objects.create(
            event_type=MarketingEvent.EventType.HIGH_CONVERSION,
            title=f"High conversion campaign: {instance.name}",
            description=f"Campaign achieved {instance.conversion_rate:.1f}% conversion rate",
            campaign=instance,
            tenant=instance.tenant,
            store=instance.store,
            event_data={'conversion_rate': instance.conversion_rate}
        )


@receiver(post_save, sender=MarketingCampaign)
def track_low_performance(sender, instance, **kwargs):
    """Track low performance campaigns"""
    if instance.conversion_rate < 1.0 and instance.messages_sent > 100:  # Low performance threshold
        MarketingEvent.objects.create(
            event_type=MarketingEvent.EventType.LOW_PERFORMANCE,
            title=f"Low performance campaign: {instance.name}",
            description=f"Campaign has low conversion rate of {instance.conversion_rate:.1f}%",
            campaign=instance,
            tenant=instance.tenant,
            store=instance.store,
            event_data={'conversion_rate': instance.conversion_rate}
        ) 