#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.products.models import Category
from apps.stores.models import Store
from apps.tenants.models import Tenant
from apps.users.models import User

def test_category_creation():
    """Test category creation for store managers"""
    
    # Find Mandeep Jewelries tenant
    try:
        tenant = Tenant.objects.get(name__icontains='mandeep')
        print(f"Found tenant: {tenant.name}")
    except Tenant.DoesNotExist:
        print("Mandeep Jewelries tenant not found")
        return
    
    # Find stores
    stores = Store.objects.filter(tenant=tenant)
    print(f"Found {stores.count()} stores:")
    for store in stores:
        print(f"  - {store.name} (ID: {store.id})")
    
    # Find store managers
    store_managers = User.objects.filter(
        role='manager',
        tenant=tenant,
        store__isnull=False
    )
    print(f"\nFound {store_managers.count()} store managers:")
    for manager in store_managers:
        print(f"  - {manager.get_full_name()} (Store: {manager.store.name})")
    
    # Check existing categories
    categories = Category.objects.filter(tenant=tenant)
    print(f"\nExisting categories ({categories.count()}):")
    for category in categories:
        store_info = f" (Store: {category.store.name})" if category.store else " (Global)"
        print(f"  - {category.name}{store_info}")
    
    # Test creating categories for each store
    for store in stores:
        print(f"\n--- Testing category creation for {store.name} ---")
        
        # Create a test category for this store
        test_category_name = f"Test Category - {store.name}"
        
        # Check if category already exists
        if Category.objects.filter(name=test_category_name, tenant=tenant).exists():
            print(f"  Category '{test_category_name}' already exists")
            continue
        
        # Create the category
        category = Category.objects.create(
            name=test_category_name,
            description=f"Test category for {store.name}",
            tenant=tenant,
            store=store,
            scope='store',
            is_active=True
        )
        print(f"  ✅ Created category: {category.name}")
        print(f"     Store: {category.store.name}")
        print(f"     Scope: {category.scope}")
    
    # Final category count
    final_categories = Category.objects.filter(tenant=tenant)
    print(f"\nFinal category count: {final_categories.count()}")
    
    # Show categories by store
    for store in stores:
        store_categories = Category.objects.filter(tenant=tenant, store=store)
        print(f"  {store.name}: {store_categories.count()} categories")
    
    global_categories = Category.objects.filter(tenant=tenant, scope='global')
    print(f"  Global categories: {global_categories.count()}")

if __name__ == '__main__':
    test_category_creation() 