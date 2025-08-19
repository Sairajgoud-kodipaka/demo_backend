from django.contrib import admin
from .models import BusinessSetting, Tag, NotificationTemplate, BrandingSetting, LegalSetting

admin.site.register(BusinessSetting)
admin.site.register(Tag)
admin.site.register(NotificationTemplate)
admin.site.register(BrandingSetting)
admin.site.register(LegalSetting) 