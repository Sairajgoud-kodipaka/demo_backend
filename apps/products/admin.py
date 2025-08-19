from django.contrib import admin
from .models import Product, Category, ProductVariant, ProductInventory, StockTransfer

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'status', 'quantity', 'tenant', 'store', 'scope')
    search_fields = ('name', 'sku')
    list_filter = ('category', 'status', 'tenant', 'store', 'scope')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'tenant', 'store', 'scope', 'is_active')
    search_fields = ('name',)
    list_filter = ('tenant', 'store', 'scope', 'is_active')

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'product', 'quantity', 'is_active')
    search_fields = ('name', 'sku')
    list_filter = ('product', 'is_active')

@admin.register(ProductInventory)
class ProductInventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'store', 'quantity', 'available_quantity', 'last_updated')
    search_fields = ('product__name', 'product__sku', 'store__name')
    list_filter = ('store', 'last_updated')
    readonly_fields = ('available_quantity', 'is_low_stock', 'is_out_of_stock')

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('product', 'from_store', 'to_store', 'quantity', 'status', 'requested_by', 'approved_by', 'created_at')
    search_fields = ('product__name', 'product__sku', 'from_store__name', 'to_store__name')
    list_filter = ('status', 'from_store', 'to_store', 'created_at')
    readonly_fields = ('requested_by', 'created_at', 'updated_at')
