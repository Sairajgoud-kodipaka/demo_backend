from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, ClientInteractionViewSet, AppointmentViewSet, FollowUpViewSet, TaskViewSet, AnnouncementViewSet, PurchaseViewSet, AuditLogViewSet, CustomerTagViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'interactions', ClientInteractionViewSet, basename='clientinteraction')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'follow-ups', FollowUpViewSet, basename='followup')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'purchases', PurchaseViewSet, basename='purchase')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')
router.register(r'tags', CustomerTagViewSet, basename='customertag')

urlpatterns = [
    path('clients/trash/', ClientViewSet.as_view({'get': 'trash'}), name='client-trash'),
    path('clients/<int:pk>/restore/', ClientViewSet.as_view({'post': 'restore'}), name='client-restore'),
    
    # Import/Export URLs
    path('clients/export/csv/', ClientViewSet.as_view({'get': 'export_csv'}), name='client-export-csv'),
    path('clients/export/json/', ClientViewSet.as_view({'get': 'export_json'}), name='client-export-json'),
    # path('clients/export/xlsx/', ClientViewSet.as_view({'get': 'export_xlsx'}), name='client-export-xlsx'),
    path('clients/import/csv/', ClientViewSet.as_view({'post': 'import_csv'}), name='client-import-csv'),
    path('clients/import/json/', ClientViewSet.as_view({'post': 'import_json'}), name='client-import-json'),
    path('clients/template/download/', ClientViewSet.as_view({'get': 'download_template'}), name='client-download-template'),
    
    path('', include(router.urls)),
] 