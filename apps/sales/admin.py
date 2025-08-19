from django.contrib import admin
from .models import Sale, SaleItem, SalesPipeline


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'client', 'sales_representative', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at', 'tenant']
    search_fields = ['order_number', 'client__first_name', 'client__last_name']
    readonly_fields = ['created_at', 'updated_at', 'order_date']
    date_hierarchy = 'created_at'


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'product', 'quantity', 'unit_price', 'total_price']
    list_filter = ['sale__status']
    search_fields = ['sale__order_number', 'product__name']


@admin.register(SalesPipeline)
class SalesPipelineAdmin(admin.ModelAdmin):
    list_display = ['title', 'client', 'sales_representative', 'stage', 'expected_value', 'probability', 'created_at']
    list_filter = ['stage', 'probability', 'created_at', 'tenant']
    search_fields = ['title', 'client__first_name', 'client__last_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
