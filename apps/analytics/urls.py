from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.dashboard_stats, name='dashboard_stats'),
    path('business-admin/', views.business_admin_dashboard, name='business_admin_dashboard'),
    path('sales/', views.sales_analytics, name='sales_analytics'),
    path('customers/', views.customer_analytics, name='customer_analytics'),
    path('products/', views.product_analytics, name='product_analytics'),
] 