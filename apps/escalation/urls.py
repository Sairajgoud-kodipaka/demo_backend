from django.urls import path
from . import views

app_name = 'escalation'

urlpatterns = [
    # Escalation management
    path('', views.EscalationListView.as_view(), name='escalation-list'),
    path('my-escalations/', views.MyEscalationsView.as_view(), name='my-escalations'),
    path('stats/', views.EscalationStatsView.as_view(), name='escalation-stats'),
    path('<int:pk>/', views.EscalationDetailView.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='escalation-detail'),
    path('<int:pk>/change_status/', views.EscalationDetailView.as_view({'post': 'change_status'}), name='escalation-change-status'),
    path('<int:pk>/assign/', views.EscalationDetailView.as_view({'post': 'assign'}), name='escalation-assign'),
    path('<int:pk>/resolve/', views.EscalationDetailView.as_view({'post': 'resolve'}), name='escalation-resolve'),
    path('<int:pk>/close/', views.EscalationDetailView.as_view({'post': 'close'}), name='escalation-close'),
    
    # Escalation notes
    path('<int:escalation_id>/notes/', views.EscalationNoteListView.as_view(), name='escalation-note-list'),
    path('<int:escalation_id>/notes/<int:pk>/', views.EscalationNoteDetailView.as_view(), name='escalation-note-detail'),
    
    # Escalation templates
    path('templates/', views.EscalationTemplateListView.as_view(), name='escalation-template-list'),
    path('templates/<int:pk>/', views.EscalationTemplateDetailView.as_view(), name='escalation-template-detail'),
] 