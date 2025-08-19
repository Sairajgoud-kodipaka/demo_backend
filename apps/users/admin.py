from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, TeamMember, TeamMemberActivity, TeamMemberPerformance


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin interface for User model.
    """
    list_display = [
        'username', 'email', 'first_name', 'last_name', 'role', 
        'tenant', 'store', 'is_active', 'last_login', 'created_at'
    ]
    list_filter = [
        'role', 'is_active', 'tenant', 'store', 'created_at', 'last_login'
    ]
    search_fields = [
        'username', 'email', 'first_name', 'last_name'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'address')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'role', 'tenant', 'store')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Profile', {'fields': ('profile_picture',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'tenant', 'store'),
        }),
    )


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    """
    Admin interface for TeamMember model.
    """
    list_display = [
        'employee_id', 'user_name', 'user_email', 'department', 'position', 
        'status', 'performance_rating', 'sales_percentage', 'manager_name', 'created_at'
    ]
    list_filter = [
        'status', 'performance_rating', 'department', 'hire_date', 'created_at'
    ]
    search_fields = [
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'employee_id', 'department', 'position'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'employee_id', 'department', 'position', 'hire_date')
        }),
        ('Status & Performance', {
            'fields': ('status', 'performance_rating', 'sales_target', 'current_sales')
        }),
        ('Management', {
            'fields': ('manager', 'skills', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['employee_id', 'created_at', 'updated_at', 'sales_percentage']
    
    def user_name(self, obj):
        return obj.user.get_full_name()
    user_name.short_description = 'Name'
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    
    def manager_name(self, obj):
        if obj.manager:
            return obj.manager.user.get_full_name()
        return '-'
    manager_name.short_description = 'Manager'
    
    def sales_percentage(self, obj):
        percentage = obj.sales_percentage
        color = 'green' if percentage >= 100 else 'orange' if percentage >= 80 else 'red'
        return format_html(
            '<span style="color: {};">{}%</span>',
            color, f'{percentage:.1f}'
        )
    sales_percentage.short_description = 'Sales %'


@admin.register(TeamMemberActivity)
class TeamMemberActivityAdmin(admin.ModelAdmin):
    """
    Admin interface for TeamMemberActivity model.
    """
    list_display = [
        'team_member_name', 'activity_type', 'description', 'created_at'
    ]
    list_filter = [
        'activity_type', 'created_at', 'team_member__department'
    ]
    search_fields = [
        'team_member__user__first_name', 'team_member__user__last_name',
        'team_member__user__email', 'description'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('team_member', 'activity_type', 'description', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def team_member_name(self, obj):
        return obj.team_member.user.get_full_name()
    team_member_name.short_description = 'Team Member'


@admin.register(TeamMemberPerformance)
class TeamMemberPerformanceAdmin(admin.ModelAdmin):
    """
    Admin interface for TeamMemberPerformance model.
    """
    list_display = [
        'team_member_name', 'month', 'sales_target', 'actual_sales', 
        'sales_percentage', 'leads_generated', 'deals_closed', 'conversion_rate'
    ]
    list_filter = [
        'month', 'team_member__department', 'team_member__status'
    ]
    search_fields = [
        'team_member__user__first_name', 'team_member__user__last_name',
        'team_member__user__email'
    ]
    ordering = ['-month', '-created_at']
    
    fieldsets = (
        ('Performance Information', {
            'fields': ('team_member', 'month', 'sales_target', 'actual_sales')
        }),
        ('Metrics', {
            'fields': ('leads_generated', 'deals_closed', 'customer_satisfaction')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'sales_percentage', 'conversion_rate']
    
    def team_member_name(self, obj):
        return obj.team_member.user.get_full_name()
    team_member_name.short_description = 'Team Member'
    
    def sales_percentage(self, obj):
        percentage = obj.sales_percentage
        color = 'green' if percentage >= 100 else 'orange' if percentage >= 80 else 'red'
        return format_html(
            '<span style="color: {};">{}%</span>',
            color, f'{percentage:.1f}'
        )
    sales_percentage.short_description = 'Sales %'
    
    def conversion_rate(self, obj):
        rate = obj.conversion_rate
        color = 'green' if rate >= 20 else 'orange' if rate >= 10 else 'red'
        return format_html(
            '<span style="color: {};">{}%</span>',
            color, f'{rate:.1f}'
        )
    conversion_rate.short_description = 'Conversion %'
