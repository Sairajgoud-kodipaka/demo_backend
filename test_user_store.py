#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant
from apps.stores.models import Store, StoreUserMap
from apps.products.models import Product, Category

User = get_user_model()

def test_user_store_assignment():
    print("Testing user store assignment...")
    
    # Check existing users and their store assignments
    users = User.objects.all()
    print(f"\nTotal users: {users.count()}")
    
    for user in users:
        print(f"User: {user.username} (ID: {user.id})")
        print(f"  Role: {user.role}")
        print(f"  Tenant: {user.tenant}")
        print(f"  Store: {user.store}")
        print(f"  Store ID: {user.store.id if user.store else 'None'}")
        
        # Check StoreUserMap entries
        store_maps = StoreUserMap.objects.filter(user=user)
        print(f"  StoreUserMap entries: {store_maps.count()}")
        for map_entry in store_maps:
            print(f"    - Store: {map_entry.store.name}, Role: {map_entry.role}")
        print()
    
    # Check stores
    stores = Store.objects.all()
    print(f"\nTotal stores: {stores.count()}")
    for store in stores:
        print(f"Store: {store.name} (ID: {store.id})")
        print(f"  Tenant: {store.tenant}")
        print(f"  Users: {store.users.count()}")
        for user in store.users.all():
            print(f"    - {user.username} ({user.role})")
        print()
    
    # Test product creation for a manager user
    manager_users = User.objects.filter(role='manager')
    if manager_users.exists():
        test_user = manager_users.first()
        print(f"\nTesting product creation for manager: {test_user.username}")
        print(f"  Store: {test_user.store}")
        print(f"  Store ID: {test_user.store.id if test_user.store else 'None'}")
        
        if test_user.store:
            # Test creating a product
            product_data = {
                'name': 'Test Product from Manager',
                'sku': 'TEST-MANAGER-001',
                'description': 'Test product created by manager',
                'brand': 'Test Brand',
                'cost_price': 100.00,
                'selling_price': 150.00,
                'discount_price': 0.00,
                'quantity': 10,
                'min_quantity': 1,
                'max_quantity': 100,
                'weight': 5.0,
                'dimensions': '10x5x2 cm',
                'material': 'Gold',
                'color': 'Yellow',
                'size': '18K',
                'status': 'active',
                'is_featured': False,
                'is_bestseller': False,
            }
            
            # Create product directly using the model
            product = Product.objects.create(
                **product_data,
                store=test_user.store,
                scope='store',
                tenant=test_user.tenant
            )
            print(f"  Product created successfully: {product.name} (ID: {product.id})")
            print(f"  Store: {product.store}")
            print(f"  Scope: {product.scope}")
        else:
            print("  No store assigned to manager user")
    else:
        print("\nNo manager users found")

if __name__ == '__main__':
    test_user_store_assignment() 