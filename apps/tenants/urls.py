from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    path('', views.TenantListView.as_view(), name='tenant-list'),
    path('create/', views.TenantCreateView.as_view(), name='tenant-create'),
    path('<int:pk>/', views.TenantDetailView.as_view(), name='tenant-detail'),
    path('<int:pk>/update/', views.TenantUpdateView.as_view(), name='tenant-update'),
    path('<int:pk>/delete/', views.TenantDeleteView.as_view(), name='tenant-delete'),
    path('dashboard/', views.BusinessDashboardView.as_view(), name='business-dashboard'),
    path('platform-dashboard/', views.PlatformAdminDashboardView.as_view(), name='platform-dashboard'),
    path('manager-dashboard/', views.ManagerDashboardView.as_view(), name='manager-dashboard'),
] 