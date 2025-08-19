from django.db import models
from django.utils.translation import gettext_lazy as _


class AutomationWorkflow(models.Model):
    """
    Model for defining automation workflows.
    """
    class TriggerType(models.TextChoices):
        EVENT = 'event', _('Event')
        SCHEDULE = 'schedule', _('Schedule')
        MANUAL = 'manual', _('Manual')
        CONDITION = 'condition', _('Condition')

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        DRAFT = 'draft', _('Draft')

    # Workflow Information
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Trigger Configuration
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices)
    trigger_config = models.JSONField(default=dict, blank=True)
    
    # Conditions
    conditions = models.JSONField(default=list, blank=True)
    
    # Actions
    actions = models.JSONField(default=list, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    is_enabled = models.BooleanField(default=False)
    
    # Execution Settings
    max_executions = models.PositiveIntegerField(default=0, help_text=_('0 for unlimited'))
    execution_count = models.PositiveIntegerField(default=0)
    last_executed = models.DateTimeField(blank=True, null=True)
    
    # Tenant relationship
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='automation_workflows'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Automation Workflow')
        verbose_name_plural = _('Automation Workflows')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_limit_reached(self):
        if self.max_executions == 0:
            return False
        return self.execution_count >= self.max_executions


class AutomationExecution(models.Model):
    """
    Model for tracking automation workflow executions.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        RUNNING = 'running', _('Running')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')

    # Execution Information
    workflow = models.ForeignKey(
        AutomationWorkflow,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    
    # Status and Progress
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    progress = models.PositiveIntegerField(default=0, help_text=_('Progress percentage'))
    
    # Input and Output
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Execution Details
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)
    
    # Trigger Information
    triggered_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_automations'
    )
    trigger_data = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Automation Execution')
        verbose_name_plural = _('Automation Executions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.workflow.name} - {self.status} - {self.created_at}"

    @property
    def is_completed(self):
        return self.status in [self.Status.COMPLETED, self.Status.FAILED, self.Status.CANCELLED]


class ScheduledTask(models.Model):
    """
    Model for scheduling recurring tasks.
    """
    class TaskType(models.TextChoices):
        EMAIL = 'email', _('Email')
        NOTIFICATION = 'notification', _('Notification')
        REPORT = 'report', _('Report')
        DATA_SYNC = 'data_sync', _('Data Sync')
        CLEANUP = 'cleanup', _('Cleanup')
        CUSTOM = 'custom', _('Custom Task')

    class Frequency(models.TextChoices):
        MINUTELY = 'minutely', _('Every Minute')
        HOURLY = 'hourly', _('Hourly')
        DAILY = 'daily', _('Daily')
        WEEKLY = 'weekly', _('Weekly')
        MONTHLY = 'monthly', _('Monthly')
        YEARLY = 'yearly', _('Yearly')
        CUSTOM = 'custom', _('Custom')

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        PAUSED = 'paused', _('Paused')

    # Task Information
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    task_type = models.CharField(max_length=20, choices=TaskType.choices)
    
    # Schedule Configuration
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    schedule_config = models.JSONField(default=dict, blank=True)
    
    # Task Configuration
    task_config = models.JSONField(default=dict, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    is_enabled = models.BooleanField(default=True)
    
    # Execution Tracking
    last_executed = models.DateTimeField(blank=True, null=True)
    next_execution = models.DateTimeField(blank=True, null=True)
    execution_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    
    # Error Handling
    max_retries = models.PositiveIntegerField(default=3)
    retry_delay_minutes = models.PositiveIntegerField(default=5)
    
    # Tenant relationship
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='scheduled_tasks'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Scheduled Task')
        verbose_name_plural = _('Scheduled Tasks')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"

    @property
    def success_rate(self):
        if self.execution_count == 0:
            return 0
        return (self.success_count / self.execution_count) * 100

    @property
    def is_overdue(self):
        if not self.next_execution:
            return False
        from django.utils import timezone
        return self.next_execution < timezone.now()


class TaskExecution(models.Model):
    """
    Model for tracking individual task executions.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        RUNNING = 'running', _('Running')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')

    # Execution Information
    task = models.ForeignKey(
        ScheduledTask,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    
    # Status and Progress
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    progress = models.PositiveIntegerField(default=0)
    
    # Input and Output
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Execution Details
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)
    
    # Retry Information
    retry_count = models.PositiveIntegerField(default=0)
    is_retry = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Task Execution')
        verbose_name_plural = _('Task Executions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task.name} - {self.status} - {self.created_at}"

    @property
    def is_completed(self):
        return self.status in [self.Status.COMPLETED, self.Status.FAILED, self.Status.CANCELLED]
