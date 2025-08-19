from django.contrib import admin
from .models import Feedback, FeedbackResponse, FeedbackSurvey, FeedbackQuestion, FeedbackSubmission


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['title', 'client', 'category', 'overall_rating', 'status', 'sentiment', 'created_at']
    list_filter = ['status', 'category', 'sentiment', 'is_public', 'is_anonymous', 'created_at']
    search_fields = ['title', 'content', 'client__name', 'client__email']
    readonly_fields = ['created_at', 'updated_at', 'reviewed_at', 'actioned_at', 'sentiment', 'sentiment_score']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'content', 'category', 'status')
        }),
        ('Ratings', {
            'fields': ('overall_rating', 'product_rating', 'service_rating', 'value_rating')
        }),
        ('Relationships', {
            'fields': ('client', 'submitted_by', 'reviewed_by', 'tenant')
        }),
        ('Sentiment Analysis', {
            'fields': ('sentiment', 'sentiment_score'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_anonymous', 'is_public', 'tags')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'reviewed_at', 'actioned_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(tenant=request.user.tenant)


@admin.register(FeedbackResponse)
class FeedbackResponseAdmin(admin.ModelAdmin):
    list_display = ['feedback', 'author', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at', 'author']
    search_fields = ['content', 'feedback__title', 'author__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(feedback__tenant=request.user.tenant)


@admin.register(FeedbackSurvey)
class FeedbackSurveyAdmin(admin.ModelAdmin):
    list_display = ['name', 'survey_type', 'is_active', 'tenant', 'created_at']
    list_filter = ['survey_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(tenant=request.user.tenant)


@admin.register(FeedbackQuestion)
class FeedbackQuestionAdmin(admin.ModelAdmin):
    list_display = ['survey', 'question_text', 'question_type', 'is_required', 'order']
    list_filter = ['question_type', 'is_required', 'survey']
    search_fields = ['question_text', 'survey__name']
    ordering = ['survey', 'order']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(survey__tenant=request.user.tenant)


@admin.register(FeedbackSubmission)
class FeedbackSubmissionAdmin(admin.ModelAdmin):
    list_display = ['survey', 'client', 'submitted_at', 'ip_address']
    list_filter = ['submitted_at', 'survey']
    search_fields = ['survey__name', 'client__name', 'client__email']
    readonly_fields = ['submitted_at', 'ip_address', 'user_agent']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(survey__tenant=request.user.tenant)
