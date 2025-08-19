from django.contrib import admin
from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'subscription_plan', 'subscription_status', 'is_active', 'created_at']
    list_filter = ['subscription_plan', 'subscription_status', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'email']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'business_type', 'industry', 'description')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address', 'website')
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'subscription_status', 'subscription_start', 'subscription_end')
        }),
        ('Settings', {
            'fields': ('is_active', 'max_users', 'max_storage_gb')
        }),
    )
