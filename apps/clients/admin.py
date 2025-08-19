from django.contrib import admin
from .models import Client, CustomerTag, ClientInteraction, Appointment, FollowUp, Task, Announcement, Purchase, AuditLog

class ClientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'customer_type', 'tenant', 'created_at', 'is_deleted', 'deleted_at')
    search_fields = ["first_name", "last_name", "email", "phone"]
    list_filter = ["customer_type", "tenant", "created_at"]

# Register your models here
admin.site.register(Client, ClientAdmin)
admin.site.register(CustomerTag)
admin.site.register(ClientInteraction)
admin.site.register(Appointment)
admin.site.register(FollowUp)
admin.site.register(Task)
admin.site.register(Announcement)
admin.site.register(Purchase)
admin.site.register(AuditLog)
