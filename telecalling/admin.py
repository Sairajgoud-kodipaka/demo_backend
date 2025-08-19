from django.contrib import admin
from .models import Assignment, CallLog, FollowUp


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['telecaller', 'customer_visit', 'status', 'created_at', 'scheduled_time']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['telecaller__username', 'customer_visit__customer_name', 'customer_visit__customer_phone']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'call_status', 'call_duration', 'customer_sentiment', 'created_at']
    list_filter = ['call_status', 'customer_sentiment', 'created_at']
    search_fields = ['assignment__customer_visit__customer_name', 'feedback']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'scheduled_time', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'scheduled_time']
    search_fields = ['assignment__customer_visit__customer_name', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'scheduled_time'
