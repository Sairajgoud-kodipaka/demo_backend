#!/usr/bin/env python
"""
Test script to verify stock transfer notifications are working
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.products.models import Product, StockTransfer, ProductInventory
from apps.stores.models import Store
from apps.tenants.models import Tenant
from apps.notifications.models import Notification
from apps.products.services import StockTransferNotificationService

User = get_user_model()

def test_stock_transfer_notifications():
    """Test the stock transfer notification system"""
    
    print("🧪 Testing Stock Transfer Notifications")
    print("=" * 50)
    
    # Get or create test data
    try:
        # Get first tenant
        tenant = Tenant.objects.first()
        if not tenant:
            print("❌ No tenant found. Please create a tenant first.")
            return
        
        # Get or create stores
        store1, created = Store.objects.get_or_create(
            name="Test Store 1",
            tenant=tenant,
            defaults={
                'code': 'TS1',
                'address': 'Test Address 1',
                'city': 'Test City',
                'state': 'Test State',
                'timezone': 'Asia/Kolkata'
            }
        )
        
        store2, created = Store.objects.get_or_create(
            name="Test Store 2", 
            tenant=tenant,
            defaults={
                'code': 'TS2',
                'address': 'Test Address 2',
                'city': 'Test City',
                'state': 'Test State',
                'timezone': 'Asia/Kolkata'
            }
        )
        
        # Get or create users
        user1, created = User.objects.get_or_create(
            username='test_user1',
            defaults={
                'email': 'user1@test.com',
                'first_name': 'Test',
                'last_name': 'User1',
                'role': 'manager',
                'tenant': tenant,
                'store': store1
            }
        )
        
        user2, created = User.objects.get_or_create(
            username='test_user2',
            defaults={
                'email': 'user2@test.com',
                'first_name': 'Test',
                'last_name': 'User2',
                'role': 'manager',
                'tenant': tenant,
                'store': store2
            }
        )
        
        # Get or create a product
        product, created = Product.objects.get_or_create(
            name="Test Product",
            tenant=tenant,
            store=store1,
            defaults={
                'sku': 'TEST001',
                'description': 'Test product for notifications',
                'cost_price': 1000,
                'selling_price': 1500,
                'quantity': 10,
                'status': 'active'
            }
        )
        
        # Create inventory for the product
        inventory, created = ProductInventory.objects.get_or_create(
            product=product,
            store=store1,
            defaults={
                'quantity': 10,
                'reorder_point': 2,
                'max_stock': 20
            }
        )
        
        print(f"✅ Test data created/retrieved:")
        print(f"   - Tenant: {tenant.name}")
        print(f"   - Store 1: {store1.name}")
        print(f"   - Store 2: {store2.name}")
        print(f"   - User 1: {user1.get_full_name()} (Store: {user1.store.name})")
        print(f"   - User 2: {user2.get_full_name()} (Store: {user2.store.name})")
        print(f"   - Product: {product.name} (SKU: {product.sku})")
        print(f"   - Inventory: {inventory.quantity} units in {store1.name}")
        
        # Test 1: Create transfer request
        print("\n📤 Test 1: Creating transfer request...")
        transfer = StockTransfer.objects.create(
            from_store=store1,
            to_store=store2,
            product=product,
            quantity=5,
            reason="Test transfer for notifications",
            requested_by=user1,
            status='pending'
        )
        
        print(f"   ✅ Transfer created: {transfer.product.name} ({transfer.quantity} units)")
        print(f"   From: {transfer.from_store.name} → To: {transfer.to_store.name}")
        
        # Test notification for transfer request
        print("\n🔔 Testing transfer request notification...")
        StockTransferNotificationService.notify_transfer_request(transfer)
        
        # Check if notifications were created
        request_notifications = Notification.objects.filter(
            type='stock_transfer_request'
        )
        print(f"   ✅ {request_notifications.count()} transfer request notifications created")
        
        # Test 2: Approve transfer
        print("\n✅ Test 2: Approving transfer...")
        transfer.approve(user2)
        print(f"   ✅ Transfer approved by {user2.get_full_name()}")
        
        # Test notification for transfer approval
        print("\n🔔 Testing transfer approval notification...")
        StockTransferNotificationService.notify_transfer_approved(transfer)
        
        # Check if notifications were created
        approval_notifications = Notification.objects.filter(
            type='stock_transfer_approved'
        )
        print(f"   ✅ {approval_notifications.count()} transfer approval notifications created")
        
        # Test 3: Complete transfer
        print("\n📦 Test 3: Completing transfer...")
        success = transfer.complete()
        if success:
            print(f"   ✅ Transfer completed successfully")
            print(f"   📊 Inventory updated:")
            print(f"      {store1.name}: {ProductInventory.objects.get(product=product, store=store1).quantity} units")
            print(f"      {store2.name}: {ProductInventory.objects.get(product=product, store=store2).quantity} units")
        else:
            print(f"   ❌ Transfer completion failed")
        
        # Test notification for transfer completion
        print("\n🔔 Testing transfer completion notification...")
        StockTransferNotificationService.notify_transfer_completed(transfer)
        
        # Check if notifications were created
        completion_notifications = Notification.objects.filter(
            type='stock_transfer_completed'
        )
        print(f"   ✅ {completion_notifications.count()} transfer completion notifications created")
        
        # Test 4: Create another transfer for cancellation test
        print("\n❌ Test 4: Testing transfer cancellation...")
        transfer2 = StockTransfer.objects.create(
            from_store=store1,
            to_store=store2,
            product=product,
            quantity=3,
            reason="Test transfer for cancellation",
            requested_by=user1,
            status='pending'
        )
        
        print(f"   ✅ Transfer 2 created: {transfer2.product.name} ({transfer2.quantity} units)")
        
        # Cancel the transfer
        transfer2.cancel()
        print(f"   ✅ Transfer 2 cancelled")
        
        # Test notification for transfer cancellation
        print("\n🔔 Testing transfer cancellation notification...")
        StockTransferNotificationService.notify_transfer_cancelled(transfer2)
        
        # Check if notifications were created
        cancellation_notifications = Notification.objects.filter(
            type='stock_transfer_cancelled'
        )
        print(f"   ✅ {cancellation_notifications.count()} transfer cancellation notifications created")
        
        # Summary
        print("\n📊 Summary:")
        print("=" * 50)
        total_notifications = Notification.objects.filter(
            type__in=['stock_transfer_request', 'stock_transfer_approved', 'stock_transfer_completed', 'stock_transfer_cancelled']
        ).count()
        print(f"   Total stock transfer notifications created: {total_notifications}")
        
        # Show notification details
        print("\n📋 Notification Details:")
        for notification in Notification.objects.filter(
            type__in=['stock_transfer_request', 'stock_transfer_approved', 'stock_transfer_completed', 'stock_transfer_cancelled']
        ).order_by('-created_at')[:10]:
            print(f"   - {notification.type}: {notification.title}")
            print(f"     Message: {notification.message[:60]}...")
            print(f"     User: {notification.user.get_full_name()}")
            print(f"     Store: {notification.store.name if notification.store else 'N/A'}")
            print(f"     Created: {notification.created_at}")
            print()
        
        print("✅ All stock transfer notification tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_stock_transfer_notifications()
