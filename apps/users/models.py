from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class User(AbstractUser):
    """
    Custom User model with role-based access control.
    """
    class Role(models.TextChoices):
        PLATFORM_ADMIN = 'platform_admin', _('Platform Admin')
        BUSINESS_ADMIN = 'business_admin', _('Business Admin')
        MANAGER = 'manager', _('Manager')
        INHOUSE_SALES = 'inhouse_sales', _('In-house Sales')
        TELE_CALLING = 'tele_calling', _('Tele-calling')
        MARKETING = 'marketing', _('Marketing')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.INHOUSE_SALES,
        help_text=_('User role in the system')
    )
    
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    
    # Tenant relationship (for multi-tenancy)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users'
    )

    # Store relationship (each user belongs to one store, except platform/business admins)
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text=_('Store this user belongs to (null for platform/business admins)')
    )
    
    # Additional fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_platform_admin(self):
        return self.role == self.Role.PLATFORM_ADMIN

    @property
    def is_business_admin(self):
        return self.role == self.Role.BUSINESS_ADMIN

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_sales_user(self):
        return self.role in [self.Role.INHOUSE_SALES, self.Role.TELE_CALLING]

    @property
    def is_marketing_user(self):
        return self.role == self.Role.MARKETING

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username


class TeamMember(models.Model):
    """
    Team Member model for managing team-specific information and performance.
    """
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        SUSPENDED = 'suspended', _('Suspended')
        ON_LEAVE = 'on_leave', _('On Leave')

    class Performance(models.TextChoices):
        EXCELLENT = 'excellent', _('Excellent')
        GOOD = 'good', _('Good')
        AVERAGE = 'average', _('Average')
        BELOW_AVERAGE = 'below_average', _('Below Average')
        POOR = 'poor', _('Poor')

    # Core user relationship
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='team_member',
        help_text=_('Associated user account')
    )
    
    # Team management fields
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        help_text=_('Unique employee identifier')
    )
    
    department = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_('Department or team')
    )
    
    position = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_('Job position or title')
    )
    
    hire_date = models.DateField(
        default=timezone.now,
        help_text=_('Date when team member was hired')
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text=_('Current status of the team member')
    )
    
    # Performance tracking
    performance_rating = models.CharField(
        max_length=20,
        choices=Performance.choices,
        blank=True,
        null=True,
        help_text=_('Current performance rating')
    )
    
    sales_target = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_('Monthly sales target')
    )
    
    current_sales = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_('Current month sales')
    )
    
    # Manager relationship
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',
        help_text=_('Direct manager or supervisor')
    )
    
    # Additional information
    skills = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of skills and competencies')
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text=_('Additional notes about the team member')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Team Member')
        verbose_name_plural = _('Team Members')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.employee_id}"

    @property
    def sales_percentage(self):
        """Calculate sales achievement percentage."""
        if self.sales_target > 0:
            return (self.current_sales / self.sales_target) * 100
        return 0

    @property
    def is_performing_well(self):
        """Check if team member is performing well."""
        return self.performance_rating in [self.Performance.EXCELLENT, self.Performance.GOOD]

    def get_performance_color(self):
        """Get color class for performance rating."""
        color_map = {
            self.Performance.EXCELLENT: 'text-green-600',
            self.Performance.GOOD: 'text-blue-600',
            self.Performance.AVERAGE: 'text-yellow-600',
            self.Performance.BELOW_AVERAGE: 'text-orange-600',
            self.Performance.POOR: 'text-red-600',
        }
        return color_map.get(self.performance_rating, 'text-gray-600')

    def save(self, *args, **kwargs):
        # Generate employee ID if not provided
        if not self.employee_id:
            last_member = TeamMember.objects.order_by('-employee_id').first()
            if last_member and last_member.employee_id.isdigit():
                next_id = int(last_member.employee_id) + 1
            else:
                next_id = 1001
            self.employee_id = str(next_id)
        
        super().save(*args, **kwargs)


class TeamMemberActivity(models.Model):
    """
    Track team member activities and performance metrics.
    """
    class ActivityType(models.TextChoices):
        LOGIN = 'login', _('Login')
        LOGOUT = 'logout', _('Logout')
        SALE = 'sale', _('Sale Made')
        LEAD_CREATED = 'lead_created', _('Lead Created')
        CUSTOMER_CONTACT = 'customer_contact', _('Customer Contact')
        TASK_COMPLETED = 'task_completed', _('Task Completed')
        PERFORMANCE_REVIEW = 'performance_review', _('Performance Review')

    team_member = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name='activities',
        help_text=_('Team member who performed the activity')
    )
    
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        help_text=_('Type of activity performed')
    )
    
    description = models.TextField(
        help_text=_('Description of the activity')
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional data related to the activity')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Team Member Activity')
        verbose_name_plural = _('Team Member Activities')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.team_member.user.get_full_name()} - {self.get_activity_type_display()}"


class TeamMemberPerformance(models.Model):
    """
    Monthly performance tracking for team members.
    """
    team_member = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name='performance_records',
        help_text=_('Team member performance record')
    )
    
    month = models.DateField(
        help_text=_('Month for this performance record')
    )
    
    sales_target = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_('Monthly sales target')
    )
    
    actual_sales = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_('Actual sales achieved')
    )
    
    leads_generated = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of leads generated')
    )
    
    deals_closed = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of deals closed')
    )
    
    customer_satisfaction = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Customer satisfaction rating (1-5)')
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text=_('Performance notes and comments')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Team Member Performance')
        verbose_name_plural = _('Team Member Performance')
        unique_together = ['team_member', 'month']
        ordering = ['-month']

    def __str__(self):
        return f"{self.team_member.user.get_full_name()} - {self.month.strftime('%B %Y')}"

    @property
    def sales_percentage(self):
        """Calculate sales achievement percentage."""
        if self.sales_target > 0:
            return (self.actual_sales / self.sales_target) * 100
        return 0

    @property
    def conversion_rate(self):
        """Calculate lead to deal conversion rate."""
        if self.leads_generated > 0:
            return (self.deals_closed / self.leads_generated) * 100
        return 0
