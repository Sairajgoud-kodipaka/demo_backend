from django.urls import path
from . import views

app_name = 'automation'

urlpatterns = [
    # Workflows
    path('workflows/', views.AutomationWorkflowListView.as_view(), name='workflow-list'),
    path('workflows/create/', views.AutomationWorkflowCreateView.as_view(), name='workflow-create'),
    path('workflows/<int:pk>/', views.AutomationWorkflowDetailView.as_view(), name='workflow-detail'),
    path('workflows/<int:pk>/update/', views.AutomationWorkflowUpdateView.as_view(), name='workflow-update'),
    path('workflows/<int:pk>/delete/', views.AutomationWorkflowDeleteView.as_view(), name='workflow-delete'),
    path('workflows/<int:pk>/execute/', views.AutomationWorkflowExecuteView.as_view(), name='workflow-execute'),
    
    # Workflow Executions
    path('executions/', views.AutomationExecutionListView.as_view(), name='execution-list'),
    path('executions/<int:pk>/', views.AutomationExecutionDetailView.as_view(), name='execution-detail'),
    
    # Scheduled Tasks
    path('tasks/', views.ScheduledTaskListView.as_view(), name='task-list'),
    path('tasks/create/', views.ScheduledTaskCreateView.as_view(), name='task-create'),
    path('tasks/<int:pk>/', views.ScheduledTaskDetailView.as_view(), name='task-detail'),
    path('tasks/<int:pk>/update/', views.ScheduledTaskUpdateView.as_view(), name='task-update'),
    path('tasks/<int:pk>/delete/', views.ScheduledTaskDeleteView.as_view(), name='task-delete'),
    path('tasks/<int:pk>/execute/', views.ScheduledTaskExecuteView.as_view(), name='task-execute'),
    
    # Task Executions
    path('task-executions/', views.TaskExecutionListView.as_view(), name='task-execution-list'),
    path('task-executions/<int:pk>/', views.TaskExecutionDetailView.as_view(), name='task-execution-detail'),
] 