from django.contrib import admin
from .models import Store, StoreUserMap

class StoreAdmin(admin.ModelAdmin):
    search_fields = ['name', 'code']

admin.site.register(Store, StoreAdmin)
admin.site.register(StoreUserMap)
