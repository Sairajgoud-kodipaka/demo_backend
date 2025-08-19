from django.db import models
from django.conf import settings
from django.utils import timezone

class CustomerVisit(models.Model):
    """Step 1: In-House Sales Rep records customer visit info"""
    sales_rep = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_visits')
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True, null=True)
    interests = models.JSONField(default=list, help_text="List of product interests")
    visit_timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    lead_quality = models.CharField(max_length=20, choices=[
        ('hot', 'Hot Lead'),
        ('warm', 'Warm Lead'),
        ('cold', 'Cold Lead'),
    ], default='warm')
    assigned_to_telecaller = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Visit by {self.customer_name} - {self.visit_timestamp.strftime('%Y-%m-%d %H:%M')}"

class Assignment(models.Model):
    """Step 2: Manager assigns leads to telecallers"""
    telecaller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='telecalling_assignments')
    customer_visit = models.ForeignKey(CustomerVisit, on_delete=models.CASCADE, related_name='assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='assigned_leads')
    status = models.CharField(max_length=32, choices=[
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('follow_up', 'Follow-up Needed'),
        ('unreachable', 'Unreachable'),
    ], default='assigned')
    priority = models.CharField(max_length=20, choices=[
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ], default='medium')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    outcome = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Assignment {self.id} - {self.customer_visit.customer_name} to {self.telecaller.get_full_name()}"

class CallLog(models.Model):
    """Step 3: Telecaller logs call details and feedback"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='call_logs')
    call_status = models.CharField(max_length=32, choices=[
        ('connected', 'Connected'),
        ('no_answer', 'No Answer'),
        ('busy', 'Busy'),
        ('wrong_number', 'Wrong Number'),
        ('not_interested', 'Not Interested'),
        ('call_back', 'Call Back Later'),
    ])
    call_duration = models.IntegerField(help_text="Duration in seconds", default=0)
    feedback = models.TextField(blank=True)
    customer_sentiment = models.CharField(max_length=20, choices=[
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ], default='neutral')
    revisit_required = models.BooleanField(default=False)
    revisit_notes = models.TextField(blank=True)
    recording_url = models.URLField(blank=True, null=True)
    disposition_code = models.CharField(max_length=64, blank=True, null=True)
    call_time = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CallLog {self.id} for Assignment {self.assignment_id}"

class FollowUp(models.Model):
    """Step 4: Manager monitors and creates follow-ups"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='followups')
    scheduled_time = models.DateTimeField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ], default='pending')
    priority = models.CharField(max_length=20, choices=[
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ], default='medium')
    completed_time = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_followups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"FollowUp {self.id} for Assignment {self.assignment_id}"

class CustomerProfile(models.Model):
    """Step 5: Enhanced customer profile with sales rep notes + telecaller feedback"""
    customer_visit = models.OneToOneField(CustomerVisit, on_delete=models.CASCADE, related_name='profile')
    original_notes = models.TextField(blank=True)
    telecaller_feedback = models.TextField(blank=True)
    engagement_score = models.IntegerField(default=0, help_text="0-100 score based on interactions")
    conversion_likelihood = models.CharField(max_length=20, choices=[
        ('very_high', 'Very High'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('very_low', 'Very Low'),
    ], default='medium')
    last_contact_date = models.DateTimeField(null=True, blank=True)
    next_follow_up_date = models.DateTimeField(null=True, blank=True)
    tags = models.JSONField(default=list, help_text="Customer tags for segmentation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.customer_visit.customer_name}"

class Notification(models.Model):
    """Notification system for assignments and feedback alerts"""
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=32, choices=[
        ('assignment', 'New Assignment'),
        ('feedback', 'Feedback Received'),
        ('follow_up', 'Follow-up Reminder'),
        ('high_potential', 'High Potential Lead'),
        ('system', 'System Notification'),
    ])
    related_assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.get_full_name()} - {self.title}"

class Analytics(models.Model):
    """Analytics tracking for conversion rates and performance metrics"""
    date = models.DateField()
    total_leads = models.IntegerField(default=0)
    assigned_leads = models.IntegerField(default=0)
    connected_calls = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    avg_call_duration = models.FloatField(default=0)
    engagement_score_avg = models.FloatField(default=0)
    conversion_rate = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['date']

    def __str__(self):
        return f"Analytics for {self.date}"
