from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Client, CustomerTag
from datetime import date

@receiver(post_save, sender=Client)
def auto_apply_tags(sender, instance, created, **kwargs):
    tags_to_add = set()
    print(f"[DEBUG] Auto-tagging for client: {instance.id} - {instance.full_name}")

    # 1. Purchase Intent / Visit Reason (case-insensitive, trimmed)
    if instance.reason_for_visit:
        mapping = {
            'wedding': 'wedding-buyer',
            'gifting': 'gifting',
            'self-purchase': 'self-purchase',
            'repair': 'repair-customer',
            'browse': 'browsing-prospect',
        }
        reason = instance.reason_for_visit.strip().lower()
        slug = mapping.get(reason)
        print(f"[DEBUG] Reason for visit: '{reason}' -> Tag: {slug}")
        if slug:
            tags_to_add.add(slug)

    # 2. Product Interest (handle array of objects with mainCategory)
    if instance.customer_interests:
        for interest in instance.customer_interests:
            category = None
            if isinstance(interest, dict):
                category = interest.get('mainCategory', '').strip().lower()
            elif isinstance(interest, str):
                category = interest.strip().lower()
            print(f"[DEBUG] Product interest: '{category}'")
            if category == 'diamond':
                tags_to_add.add('diamond-interested')
            elif category == 'gold':
                tags_to_add.add('gold-interested')
            elif category == 'polki':
                tags_to_add.add('polki-interested')
        if len(instance.customer_interests) > 1:
            tags_to_add.add('mixed-buyer')

    # 3. Revenue-Based Segmentation (assume total_spend is a property or field)
    if hasattr(instance, 'total_spend'):
        print(f"[DEBUG] Total spend: {getattr(instance, 'total_spend', None)}")
        if instance.total_spend and instance.total_spend > 100000:
            tags_to_add.add('high-value')
        elif instance.total_spend and instance.total_spend > 30000:
            tags_to_add.add('mid-value')

    # 4. Demographic + Age
    if instance.date_of_birth:
        today = date.today()
        age = today.year - instance.date_of_birth.year - ((today.month, today.day) < (instance.date_of_birth.month, instance.date_of_birth.day))
        print(f"[DEBUG] Calculated age: {age}")
        if 18 <= age <= 25:
            tags_to_add.add('young-adult')
        elif 26 <= age <= 35:
            tags_to_add.add('millennial-shopper')
        elif 36 <= age <= 45:
            tags_to_add.add('middle-age-shopper')
        elif age > 46:
            tags_to_add.add('senior-shopper')

    # 5. Lead Source Tags (case-insensitive, trimmed)
    if instance.lead_source:
        mapping = {
            'instagram': 'social-lead',
            'facebook': 'facebook-lead',
            'google': 'google-lead',
            'referral': 'referral',
            'walk-in': 'walk-in',
            'other': 'other-source',
        }
        source = instance.lead_source.strip().lower()
        slug = mapping.get(source)
        print(f"[DEBUG] Lead source: '{source}' -> Tag: {slug}")
        if slug:
            tags_to_add.add(slug)

    # 6. CRM-Status Tags (case-insensitive)
    if hasattr(instance, 'status'):
        status_map = {
            'customer': 'converted-customer',
            'prospect': 'interested-lead',
            'inactive': 'not-interested',
        }
        status = str(instance.status).strip().lower()
        slug = status_map.get(status)
        print(f"[DEBUG] CRM status: '{status}' -> Tag: {slug}")
        if slug:
            tags_to_add.add(slug)
    if instance.next_follow_up:
        print(f"[DEBUG] Next follow up present, adding 'needs-follow-up'")
        tags_to_add.add('needs-follow-up')

    # 7. Community / Relationship Tags (case-insensitive, trimmed)
    if instance.community:
        mapping = {
            'hindu': 'hindu',
            'muslim': 'muslim',
            'jain': 'jain',
            'parsi': 'parsi',
            'buddhist': 'buddhist',
            'cross community': 'cross-community',
        }
        community = instance.community.strip().lower()
        slug = mapping.get(community)
        print(f"[DEBUG] Community: '{community}' -> Tag: {slug}")
        if slug:
            tags_to_add.add(slug)

    # 8. Event-Driven Tags (Birthday, Anniversary)
    today = date.today()
    if instance.date_of_birth and instance.date_of_birth.month == today.month and abs(instance.date_of_birth.day - today.day) <= 7:
        print(f"[DEBUG] Birthday this week, adding 'birthday-week'")
        tags_to_add.add('birthday-week')
    if instance.anniversary_date and instance.anniversary_date.month == today.month and abs(instance.anniversary_date.day - today.day) <= 7:
        print(f"[DEBUG] Anniversary this week, adding 'anniversary-week'")
        tags_to_add.add('anniversary-week')

    print(f"[DEBUG] Tags to add for client {instance.id}: {tags_to_add}")
    tag_objs = CustomerTag.objects.filter(slug__in=tags_to_add)
    print(f"[DEBUG] Tag objects found: {[t.slug for t in tag_objs]}")
    if tag_objs.exists():
        instance.tags.add(*tag_objs)
        print(f"[DEBUG] Tags assigned to client {instance.id}")
    else:
        print(f"[DEBUG] No tags assigned to client {instance.id}") 