from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.users.models import User
from apps.clients.models import Client


class Feedback(models.Model):
    """
    Model for collecting and managing customer feedback.
    """
    class Category(models.TextChoices):
        PRODUCT_QUALITY = 'product_quality', _('Product Quality')
        SERVICE_EXPERIENCE = 'service_experience', _('Service Experience')
        STAFF_BEHAVIOR = 'staff_behavior', _('Staff Behavior')
        STORE_AMBIENCE = 'store_ambience', _('Store Ambience')
        PRICING = 'pricing', _('Pricing')
        DELIVERY = 'delivery', _('Delivery')
        WEBSITE_EXPERIENCE = 'website_experience', _('Website Experience')
        CUSTOMER_SUPPORT = 'customer_support', _('Customer Support')
        GENERAL = 'general', _('General')

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending Review')
        REVIEWED = 'reviewed', _('Reviewed')
        ACTIONED = 'actioned', _('Action Taken')
        CLOSED = 'closed', _('Closed')
        ESCALATED = 'escalated', _('Escalated')

    class Sentiment(models.TextChoices):
        VERY_POSITIVE = 'very_positive', _('Very Positive')
        POSITIVE = 'positive', _('Positive')
        NEUTRAL = 'neutral', _('Neutral')
        NEGATIVE = 'negative', _('Negative')
        VERY_NEGATIVE = 'very_negative', _('Very Negative')

    # Basic Information
    title = models.CharField(max_length=200, help_text=_('Brief title for the feedback'))
    content = models.TextField(help_text=_('Detailed feedback content'))
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
        help_text=_('Category of the feedback')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_('Current status of the feedback')
    )

    # Ratings
    overall_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('Overall rating (1-5 stars)')
    )
    product_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_('Product rating (1-5 stars)')
    )
    service_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_('Service rating (1-5 stars)')
    )
    value_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_('Value for money rating (1-5 stars)')
    )

    # Sentiment Analysis
    sentiment = models.CharField(
        max_length=20,
        choices=Sentiment.choices,
        null=True,
        blank=True,
        help_text=_('Automated sentiment analysis')
    )
    sentiment_score = models.FloatField(
        null=True,
        blank=True,
        help_text=_('Sentiment score (-1 to 1)')
    )

    # Relationships
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='feedbacks',
        help_text=_('Client who provided the feedback')
    )
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_feedbacks',
        help_text=_('User who submitted the feedback (if different from client)')
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_feedbacks',
        help_text=_('User who reviewed the feedback')
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='feedbacks',
        help_text=_('Tenant this feedback belongs to')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    actioned_at = models.DateTimeField(null=True, blank=True)

    # Additional Information
    is_anonymous = models.BooleanField(
        default=False,
        help_text=_('Whether the feedback was submitted anonymously')
    )
    is_public = models.BooleanField(
        default=False,
        help_text=_('Whether this feedback can be displayed publicly')
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Tags for categorizing feedback')
    )

    class Meta:
        verbose_name = _('Feedback')
        verbose_name_plural = _('Feedbacks')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.client.full_name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Auto-assign sentiment based on overall rating
        if not self.sentiment and self.overall_rating:
            if self.overall_rating >= 4:
                self.sentiment = self.Sentiment.POSITIVE
                self.sentiment_score = 0.8
            elif self.overall_rating == 3:
                self.sentiment = self.Sentiment.NEUTRAL
                self.sentiment_score = 0.0
            else:
                self.sentiment = self.Sentiment.NEGATIVE
                self.sentiment_score = -0.6

        # Update timestamps when status changes
        if self.pk:
            old_instance = Feedback.objects.get(pk=self.pk)
            if old_instance.status != self.status:
                if self.status == self.Status.REVIEWED and not self.reviewed_at:
                    self.reviewed_at = timezone.now()
                elif self.status == self.Status.ACTIONED and not self.actioned_at:
                    self.actioned_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def average_rating(self):
        """Calculate average of all ratings."""
        ratings = [r for r in [self.overall_rating, self.product_rating, 
                              self.service_rating, self.value_rating] if r is not None]
        return sum(ratings) / len(ratings) if ratings else None

    @property
    def is_positive_feedback(self):
        """Check if feedback is positive (4+ stars)."""
        return self.overall_rating >= 4

    @property
    def is_negative_feedback(self):
        """Check if feedback is negative (2 or fewer stars)."""
        return self.overall_rating <= 2


class FeedbackResponse(models.Model):
    """
    Model for tracking responses to feedback.
    """
    feedback = models.ForeignKey(
        Feedback,
        on_delete=models.CASCADE,
        related_name='responses',
        help_text=_('Feedback this response is for')
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='feedback_responses',
        help_text=_('User who wrote the response')
    )
    content = models.TextField(help_text=_('Response content'))
    is_public = models.BooleanField(
        default=False,
        help_text=_('Whether this response is visible to the customer')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Feedback Response')
        verbose_name_plural = _('Feedback Responses')
        ordering = ['-created_at']

    def __str__(self):
        return f"Response to {self.feedback.title} by {self.author.username}"


class FeedbackSurvey(models.Model):
    """
    Model for creating feedback surveys.
    """
    class SurveyType(models.TextChoices):
        POST_PURCHASE = 'post_purchase', _('Post Purchase')
        SERVICE_EVALUATION = 'service_evaluation', _('Service Evaluation')
        SATISFACTION = 'satisfaction', _('General Satisfaction')
        CUSTOM = 'custom', _('Custom Survey')

    name = models.CharField(max_length=200, help_text=_('Survey name'))
    description = models.TextField(blank=True, help_text=_('Survey description'))
    survey_type = models.CharField(
        max_length=20,
        choices=SurveyType.choices,
        default=SurveyType.SATISFACTION,
        help_text=_('Type of survey')
    )
    is_active = models.BooleanField(default=True)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='feedback_surveys'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Feedback Survey')
        verbose_name_plural = _('Feedback Surveys')
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class FeedbackQuestion(models.Model):
    """
    Model for survey questions.
    """
    class QuestionType(models.TextChoices):
        RATING = 'rating', _('Rating (1-5)')
        TEXT = 'text', _('Text Response')
        MULTIPLE_CHOICE = 'multiple_choice', _('Multiple Choice')
        YES_NO = 'yes_no', _('Yes/No')

    survey = models.ForeignKey(
        FeedbackSurvey,
        on_delete=models.CASCADE,
        related_name='questions',
        help_text=_('Survey this question belongs to')
    )
    question_text = models.CharField(max_length=500, help_text=_('Question text'))
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.RATING,
        help_text=_('Type of question')
    )
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text=_('Question order'))
    options = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Options for multiple choice questions')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Feedback Question')
        verbose_name_plural = _('Feedback Questions')
        ordering = ['survey', 'order']

    def __str__(self):
        return f"{self.survey.name} - {self.question_text[:50]}"


class FeedbackSubmission(models.Model):
    """
    Model for tracking survey submissions.
    """
    survey = models.ForeignKey(
        FeedbackSurvey,
        on_delete=models.CASCADE,
        related_name='submissions',
        help_text=_('Survey this submission is for')
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='survey_submissions',
        help_text=_('Client who submitted the survey')
    )
    answers = models.JSONField(help_text=_('Survey answers'))
    submitted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Feedback Submission')
        verbose_name_plural = _('Feedback Submissions')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.survey.name} - {self.client.full_name} ({self.submitted_at.date()})"
