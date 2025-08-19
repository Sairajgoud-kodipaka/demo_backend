"""
URL configuration for Jewelry CRM project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API Routes
    path('api/auth/', include('apps.users.urls')),
    path('api/tenants/', include('apps.tenants.urls')),
    path('api/clients/', include('apps.clients.urls')),
    path('api/', include('apps.stores.urls')),
    path('api/telecalling/', include('telecalling.urls')),
    path('api/tasks/', include('apps.tasks.urls')),
    path('api/escalation/', include('apps.escalation.urls')),
    path('api/feedback/', include('apps.feedback.urls')),
    path('api/announcements/', include('apps.announcements.urls')),
    path('api/sales/', include('apps.sales.urls')),
     path('api/products/', include('apps.products.urls')),
    path('api/integrations/', include('apps.integrations.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/automation/', include('apps.automation.urls')),
    path('api/marketing/', include('apps.marketing.urls')),
    path('api/support/', include('apps.support.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
