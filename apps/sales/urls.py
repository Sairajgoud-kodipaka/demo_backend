from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Sales
    path('list/', views.SaleListView.as_view(), name='sale-list'),
    path('create/', views.SaleCreateView.as_view(), name='sale-create'),
    path('<int:pk>/', views.SaleDetailView.as_view(), name='sale-detail'),
    path('<int:pk>/update/', views.SaleUpdateView.as_view(), name='sale-update'),
    path('<int:pk>/delete/', views.SaleDeleteView.as_view(), name='sale-delete'),
    path('export/', views.SalesExportView.as_view(), name='sale-export'),
    path('dashboard/', views.SalesDashboardView.as_view(), name='sale-dashboard'),
    
    # Sales Pipeline
    path('pipeline/', views.SalesPipelineListView.as_view(), name='pipeline-list'),
    path('pipeline/my/', views.MySalesPipelineListView.as_view(), name='pipeline-my'),
    path('pipeline/my/<int:pk>/', views.MySalesPipelineDetailView.as_view(), name='pipeline-my-detail'),
    path('pipeline/create/', views.SalesPipelineCreateView.as_view(), name='pipeline-create'),
    path('pipeline/<int:pk>/', views.SalesPipelineDetailView.as_view(), name='pipeline-detail'),
    path('pipeline/<int:pk>/update/', views.SalesPipelineUpdateView.as_view(), name='pipeline-update'),
    path('pipeline/<int:pk>/delete/', views.SalesPipelineDeleteView.as_view(), name='pipeline-delete'),
    path('pipeline/<int:pk>/transition/', views.PipelineStageTransitionView.as_view(), name='pipeline-transition'),
    path('pipeline/stats/', views.PipelineStatsView.as_view(), name='pipeline-stats'),
    path('pipeline/stages/', views.PipelineStagesView.as_view(), name='pipeline-stages'),
    path('pipeline/dashboard/', views.PipelineDashboardView.as_view(), name='pipeline-dashboard'),
    path('pipeline/export/', views.PipelineExportView.as_view(), name='pipeline-export'),
] 