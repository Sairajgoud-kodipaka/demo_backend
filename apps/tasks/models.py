from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class Goal(models.Model):
    """
    Goal model for setting and tracking goals for teams and individuals.
    """
    class GoalType(models.TextChoices):
        SALES = 'sales', _('Sales Goal')
        LEADS = 'leads', _('Lead Generation Goal')
        CUSTOMER_SATISFACTION = 'customer_satisfaction', _('Customer Satisfaction Goal')
        TASK_COMPLETION = 'task_completion', _('Task Completion Goal')
        REVENUE = 'revenue', _('Revenue Goal')
        CUSTOM = 'custom', _('Custom Goal')

    class GoalPeriod(models.TextChoices):
        DAILY = 'daily', _('Daily')
        WEEKLY = 'weekly', _('Weekly')
        MONTHLY = 'monthly', _('Monthly')
        QUARTERLY = 'quarterly', _('Quarterly')
        YEARLY = 'yearly', _('Yearly')

    # Basic information
    title = models.CharField(max_length=200, help_text=_('Goal title'))
    description = models.TextField(blank=True, null=True, help_text=_('Goal description'))
    
    # Goal type and period
    goal_type = models.CharField(
        max_length=30,
        choices=GoalType.choices,
        default=GoalType.SALES,
        help_text=_('Type of goal')
    )
    
    period = models.CharField(
        max_length=20,
        choices=GoalPeriod.choices,
        default=GoalPeriod.MONTHLY,
        help_text=_('Goal period')
    )
    
    # Target and progress
    target_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=_('Target value for the goal')
    )
    
    current_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        help_text=_('Current progress value')
    )
    
    # Date fields
    start_date = models.DateField(help_text=_('Goal start date'))
    end_date = models.DateField(help_text=_('Goal end date'))
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_goals',
        help_text=_('User assigned to this goal')
    )
    
    # Team/Store context
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='goals',
        null=True,
        blank=True,
        help_text=_('Store this goal belongs to (null for individual goals)')
    )
    
    # Status
    is_active = models.BooleanField(default=True, help_text=_('Whether the goal is active'))
    is_completed = models.BooleanField(default=False, help_text=_('Whether the goal is completed'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_goals',
        help_text=_('User who created this goal')
    )

    class Meta:
        verbose_name = _('Goal')
        verbose_name_plural = _('Goals')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.assigned_to.get_full_name()}"

    @property
    def progress_percentage(self):
        """Calculate progress percentage."""
        if self.target_value == 0:
            return 0
        return min(100, (self.current_value / self.target_value) * 100)

    @property
    def is_overdue(self):
        """Check if goal is overdue."""
        return timezone.now().date() > self.end_date and not self.is_completed

    @property
    def days_remaining(self):
        """Calculate days remaining until deadline."""
        remaining = self.end_date - timezone.now().date()
        return max(0, remaining.days)

    def update_progress(self, new_value):
        """Update goal progress."""
        self.current_value = new_value
        if self.current_value >= self.target_value:
            self.is_completed = True
        self.save()


class WorkTask(models.Model):
    """
    Task model for assigning and tracking tasks for team members.
    """
    class Priority(models.TextChoices):
        LOW = 'low', _('Low')
        MEDIUM = 'medium', _('Medium')
        HIGH = 'high', _('High')
        URGENT = 'urgent', _('Urgent')

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')
        ON_HOLD = 'on_hold', _('On Hold')

    class TaskType(models.TextChoices):
        SALES = 'sales', _('Sales Task')
        FOLLOW_UP = 'follow_up', _('Follow-up Task')
        CUSTOMER_SERVICE = 'customer_service', _('Customer Service Task')
        ADMINISTRATIVE = 'administrative', _('Administrative Task')
        TRAINING = 'training', _('Training Task')
        CUSTOM = 'custom', _('Custom Task')

    # Basic information
    title = models.CharField(max_length=200, help_text=_('Task title'))
    description = models.TextField(help_text=_('Task description'))
    
    # Task type and priority
    task_type = models.CharField(
        max_length=30,
        choices=TaskType.choices,
        default=TaskType.CUSTOM,
        help_text=_('Type of task')
    )
    
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text=_('Task priority level')
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_('Current status of the task')
    )
    
    # Assignment and dates
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_work_tasks',
        help_text=_('User assigned to this task')
    )
    
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_work_tasks',
        help_text=_('User who created/assigned this task')
    )
    
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Task due date and time')
    )
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the task was started')
    )
    
    completed_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the task was completed')
    )
    
    # Progress tracking
    progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('Task completion percentage (0-100)')
    )
    
    # Related entities
    customer = models.ForeignKey(
        'clients.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_tasks',
        help_text=_('Related customer (if applicable)')
    )
    
    goal = models.ForeignKey(
        Goal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_tasks',
        help_text=_('Related goal (if applicable)')
    )
    
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='work_tasks',
        null=True,
        blank=True,
        help_text=_('Store this task belongs to')
    )
    
    # Additional fields
    estimated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Estimated hours to complete')
    )
    
    actual_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Actual hours spent')
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text=_('Additional notes about the task')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Task')
        verbose_name_plural = _('Tasks')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.assigned_to.get_full_name()}"

    @property
    def is_overdue(self):
        """Check if task is overdue."""
        if not self.due_date:
            return False
        return timezone.now() > self.due_date and self.status not in [self.Status.COMPLETED, self.Status.CANCELLED]

    @property
    def days_remaining(self):
        """Calculate days remaining until deadline."""
        if not self.due_date:
            return 0
        remaining = self.due_date - timezone.now()
        return max(0, remaining.days)

    @property
    def is_high_priority(self):
        """Check if task is high priority."""
        return self.priority in [self.Priority.HIGH, self.Priority.URGENT]

    def start_task(self):
        """Mark task as started."""
        if self.status == self.Status.PENDING:
            self.status = self.Status.IN_PROGRESS
            self.start_date = timezone.now()
            self.save()

    def complete_task(self):
        """Mark task as completed."""
        self.status = self.Status.COMPLETED
        self.progress_percentage = 100
        self.completed_date = timezone.now()
        self.save()

    def update_progress(self, percentage):
        """Update task progress."""
        self.progress_percentage = max(0, min(100, percentage))
        if self.progress_percentage == 100:
            self.complete_task()
        elif self.status == self.Status.PENDING and self.progress_percentage > 0:
            self.status = self.Status.IN_PROGRESS
        self.save()


class TaskComment(models.Model):
    """
    Comments on tasks for collaboration and communication.
    """
    task = models.ForeignKey(
        WorkTask,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text=_('Task this comment belongs to')
    )
    
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_comments',
        help_text=_('User who wrote the comment')
    )
    
    content = models.TextField(help_text=_('Comment content'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Task Comment')
        verbose_name_plural = _('Task Comments')
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author.get_full_name()} on {self.task.title}"


class TaskAttachment(models.Model):
    """
    File attachments for tasks.
    """
    task = models.ForeignKey(
        WorkTask,
        on_delete=models.CASCADE,
        related_name='attachments',
        help_text=_('Task this attachment belongs to')
    )
    
    file = models.FileField(
        upload_to='task_attachments/',
        help_text=_('Attached file')
    )
    
    filename = models.CharField(
        max_length=255,
        help_text=_('Original filename')
    )
    
    file_size = models.PositiveIntegerField(
        help_text=_('File size in bytes')
    )
    
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_attachments',
        help_text=_('User who uploaded the file')
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Task Attachment')
        verbose_name_plural = _('Task Attachments')
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.filename} - {self.task.title}" 