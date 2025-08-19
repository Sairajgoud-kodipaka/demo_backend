from django.contrib import admin
from .models import Escalation, EscalationNote, EscalationTemplate


@admin.register(Escalation)
class EscalationAdmin(admin.ModelAdmin):
    list_display = ['title', 'client', 'category', 'priority', 'status', 'assigned_to', 'created_at', 'is_overdue']
    list_filter = ['status', 'priority', 'category', 'created_at', 'assigned_to']
    search_fields = ['title', 'description', 'client__name', 'client__email']
    readonly_fields = ['created_at', 'updated_at', 'assigned_at', 'resolved_at', 'closed_at', 'due_date']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'priority', 'status')
        }),
        ('Relationships', {
            'fields': ('client', 'created_by', 'assigned_to', 'tenant')
        }),
        ('SLA Tracking', {
            'fields': ('sla_hours', 'due_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'assigned_at', 'resolved_at', 'closed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(tenant=request.user.tenant)


@admin.register(EscalationNote)
class EscalationNoteAdmin(admin.ModelAdmin):
    list_display = ['escalation', 'author', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at', 'author']
    search_fields = ['content', 'escalation__title', 'author__username']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(escalation__tenant=request.user.tenant)


@admin.register(EscalationTemplate)
class EscalationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'tenant', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'subject', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(tenant=request.user.tenant)
