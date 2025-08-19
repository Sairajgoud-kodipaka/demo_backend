from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Goal, WorkTask, TaskComment, TaskAttachment


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'goal_type', 'period', 'assigned_to', 'target_value', 
        'current_value', 'progress_display', 'end_date', 'is_active', 
        'is_completed', 'days_remaining_display'
    ]
    list_filter = [
        'goal_type', 'period', 'is_active', 'is_completed', 'store', 
        'created_at', 'end_date'
    ]
    search_fields = ['title', 'description', 'assigned_to__username', 'assigned_to__first_name', 'assigned_to__last_name']
    list_editable = ['is_active', 'is_completed']
    readonly_fields = ['progress_display', 'days_remaining_display', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'goal_type', 'period')
        }),
        ('Target & Progress', {
            'fields': ('target_value', 'current_value', 'progress_display')
        }),
        ('Timeline', {
            'fields': ('start_date', 'end_date', 'days_remaining_display')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'store', 'created_by')
        }),
        ('Status', {
            'fields': ('is_active', 'is_completed')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_display(self, obj):
        """Display progress as a colored bar."""
        percentage = obj.progress_percentage
        color = 'green' if percentage >= 100 else 'orange' if percentage >= 50 else 'red'
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; '
            'display: flex; align-items: center; justify-content: center; color: white; '
            'font-size: 12px; font-weight: bold;">{}%</div></div>',
            percentage, color, percentage
        )
    progress_display.short_description = 'Progress'
    
    def days_remaining_display(self, obj):
        """Display days remaining with color coding."""
        days = obj.days_remaining
        if days == 0:
            return format_html('<span style="color: red; font-weight: bold;">Due Today</span>')
        elif days < 0:
            return format_html('<span style="color: red; font-weight: bold;">Overdue ({} days)</span>', abs(days))
        elif days <= 7:
            return format_html('<span style="color: orange; font-weight: bold;">{} days</span>', days)
        else:
            return format_html('<span style="color: green;">{} days</span>', days)
    days_remaining_display.short_description = 'Days Remaining'


@admin.register(WorkTask)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'task_type', 'priority', 'status', 'assigned_to', 
        'due_date', 'progress_display', 'is_overdue_display', 'store'
    ]
    list_filter = [
        'task_type', 'priority', 'status', 'store', 'goal', 
        'created_at', 'due_date'
    ]
    search_fields = [
        'title', 'description', 'assigned_to__username', 
        'assigned_to__first_name', 'assigned_to__last_name'
    ]
    list_editable = ['priority', 'status']
    readonly_fields = [
        'progress_display', 'is_overdue_display', 'days_remaining_display',
        'created_at', 'updated_at', 'start_date', 'completed_date'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'task_type', 'priority', 'status')
        }),
        ('Assignment & Timeline', {
            'fields': ('assigned_to', 'assigned_by', 'due_date', 'start_date', 'completed_date')
        }),
        ('Progress', {
            'fields': ('progress_percentage', 'progress_display', 'estimated_hours', 'actual_hours')
        }),
        ('Related Entities', {
            'fields': ('customer', 'goal', 'store')
        }),
        ('Additional Information', {
            'fields': ('notes', 'is_overdue_display', 'days_remaining_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_display(self, obj):
        """Display progress as a colored bar."""
        percentage = obj.progress_percentage
        color = 'green' if percentage >= 100 else 'orange' if percentage >= 50 else 'red'
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; '
            'display: flex; align-items: center; justify-content: center; color: white; '
            'font-size: 12px; font-weight: bold;">{}%</div></div>',
            percentage, color, percentage
        )
    progress_display.short_description = 'Progress'
    
    def is_overdue_display(self, obj):
        """Display overdue status."""
        if obj.is_overdue:
            return format_html('<span style="color: red; font-weight: bold;">OVERDUE</span>')
        return format_html('<span style="color: green;">On Time</span>')
    is_overdue_display.short_description = 'Overdue Status'
    
    def days_remaining_display(self, obj):
        """Display days remaining with color coding."""
        days = obj.days_remaining
        if days == 0:
            return format_html('<span style="color: red; font-weight: bold;">Due Today</span>')
        elif days < 0:
            return format_html('<span style="color: red; font-weight: bold;">Overdue ({} days)</span>', abs(days))
        elif days <= 3:
            return format_html('<span style="color: orange; font-weight: bold;">{} days</span>', days)
        else:
            return format_html('<span style="color: green;">{} days</span>', days)
    days_remaining_display.short_description = 'Days Remaining'


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'author', 'content_preview', 'created_at']
    list_filter = ['created_at', 'task__status', 'task__priority']
    search_fields = ['content', 'author__username', 'task__title']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def content_preview(self, obj):
        """Show a preview of the comment content."""
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'task', 'uploaded_by', 'file_size_display', 'uploaded_at']
    list_filter = ['uploaded_at', 'task__status', 'task__priority']
    search_fields = ['filename', 'task__title', 'uploaded_by__username']
    readonly_fields = ['uploaded_at', 'file_size_display']
    date_hierarchy = 'uploaded_at'
    
    def file_size_display(self, obj):
        """Display file size in human readable format."""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    file_size_display.short_description = 'File Size' 