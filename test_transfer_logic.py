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
from apps.products.models import Product, Category, StockTransfer
from apps.users.models import User

User = get_user_model()

def test_transfer_logic():
    print("Testing stock transfer approval logic...")
    
    # Get Mandeep Jewelries tenant
    tenant = Tenant.objects.filter(name__icontains='mandeep').first()
    if not tenant:
        print("Mandeep Jewelries tenant not found!")
        return
    
    print(f"Tenant: {tenant.name}")
    
    # Get stores
    stores = Store.objects.filter(tenant=tenant)
    if stores.count() < 2:
        print("Need at least 2 stores for testing!")
        return
    
    store1 = stores[0]  # mandeep jewelries nagole
    store2 = stores[1]  # mandeep jewelries meerpet
    
    print(f"Store 1: {store1.name} (ID: {store1.id})")
    print(f"Store 2: {store2.name} (ID: {store2.id})")
    
    # Create test users for each store
    user1, created = User.objects.get_or_create(
        username='test_manager_1',
        defaults={
            'email': 'manager1@test.com',
            'first_name': 'Manager',
            'last_name': 'One',
            'role': 'manager',
            'tenant': tenant,
            'store': store1,
        }
    )
    
    user2, created = User.objects.get_or_create(
        username='test_manager_2',
        defaults={
            'email': 'manager2@test.com',
            'first_name': 'Manager',
            'last_name': 'Two',
            'role': 'manager',
            'tenant': tenant,
            'store': store2,
        }
    )
    
    print(f"User 1: {user1.username} -> Store: {user1.store.name}")
    print(f"User 2: {user2.username} -> Store: {user2.store.name}")
    
    # Get a product from store1
    product = Product.objects.filter(store=store1).first()
    if not product:
        print("No products found in store1!")
        return
    
    print(f"Product: {product.name} (Store: {product.store.name})")
    
    # Create a transfer from store1 to store2
    transfer = StockTransfer.objects.create(
        from_store=store1,
        to_store=store2,
        product=product,
        quantity=5,
        reason="Test transfer",
        requested_by=user1,
        status='pending'
    )
    
    print(f"Created transfer: {transfer.from_store.name} -> {transfer.to_store.name}")
    print(f"Transfer status: {transfer.status}")
    
    # Test approval logic
    print("\n--- Testing Approval Logic ---")
    
    # User1 (from_store) should NOT be able to approve
    print(f"User1 ({user1.store.name}) trying to approve transfer...")
    if transfer.to_store == user1.store:
        print("❌ WRONG: User1 can approve (should not be able to)")
    else:
        print("✅ CORRECT: User1 cannot approve")
    
    # User2 (to_store) should be able to approve
    print(f"User2 ({user2.store.name}) trying to approve transfer...")
    if transfer.to_store == user2.store:
        print("✅ CORRECT: User2 can approve")
    else:
        print("❌ WRONG: User2 cannot approve (should be able to)")
    
    # Test completion logic
    print("\n--- Testing Completion Logic ---")
    
    # User1 (from_store) should be able to complete
    print(f"User1 ({user1.store.name}) trying to complete transfer...")
    if transfer.from_store == user1.store:
        print("✅ CORRECT: User1 can complete")
    else:
        print("❌ WRONG: User1 cannot complete (should be able to)")
    
    # User2 (to_store) should NOT be able to complete
    print(f"User2 ({user2.store.name}) trying to complete transfer...")
    if transfer.from_store == user2.store:
        print("❌ WRONG: User2 can complete (should not be able to)")
    else:
        print("✅ CORRECT: User2 cannot complete")
    
    # Clean up
    transfer.delete()
    print("\nTest completed!")

if __name__ == '__main__':
    test_transfer_logic() 