from django.db import models
from django.conf import settings

class Store(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=64)
    timezone = models.CharField(max_length=32, default='Asia/Kolkata')
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='managed_stores'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='stores',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class StoreUserMap(models.Model):
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('in_house_sales', 'In-House Sales'),
        ('marketing', 'Marketing'),
        ('tele_caller', 'Tele-Caller'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    can_view_all = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'store', 'role')
