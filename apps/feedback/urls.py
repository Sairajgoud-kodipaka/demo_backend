from django.urls import path
from . import views

app_name = 'feedback'

urlpatterns = [
    # Feedback management
    path('', views.FeedbackListView.as_view(), name='feedback-list'),
    path('stats/', views.FeedbackStatsView.as_view(), name='feedback-stats'),
    path('<int:pk>/', views.FeedbackDetailView.as_view(), name='feedback-detail'),
    
    # Feedback actions
    path('<int:pk>/mark_reviewed/', views.FeedbackActionsViewSet.as_view({'post': 'mark_reviewed'}), name='feedback-mark-reviewed'),
    path('<int:pk>/escalate/', views.FeedbackActionsViewSet.as_view({'post': 'escalate'}), name='feedback-escalate'),
    
    # Feedback responses
    path('<int:feedback_id>/responses/', views.FeedbackResponseListView.as_view(), name='feedback-response-list'),
    path('<int:feedback_id>/responses/<int:pk>/', views.FeedbackResponseDetailView.as_view(), name='feedback-response-detail'),
    
    # Feedback surveys
    path('surveys/', views.FeedbackSurveyListView.as_view(), name='feedback-survey-list'),
    path('surveys/stats/', views.FeedbackSurveyStatsView.as_view(), name='feedback-survey-stats'),
    path('surveys/<int:pk>/', views.FeedbackSurveyDetailView.as_view(), name='feedback-survey-detail'),
    
    # Survey questions
    path('surveys/<int:survey_id>/questions/', views.FeedbackQuestionListView.as_view(), name='feedback-question-list'),
    path('surveys/<int:survey_id>/questions/<int:pk>/', views.FeedbackQuestionDetailView.as_view(), name='feedback-question-detail'),
    
    # Survey submissions
    path('surveys/<int:survey_id>/submissions/', views.FeedbackSubmissionListView.as_view(), name='feedback-submission-list'),
    path('surveys/<int:survey_id>/submissions/<int:pk>/', views.FeedbackSubmissionDetailView.as_view(), name='feedback-submission-detail'),
    
    # Public endpoints
    path('public/', views.PublicFeedbackView.as_view(), name='public-feedback'),
    path('submit/', views.SubmitFeedbackView.as_view(), name='submit-feedback'),
] 