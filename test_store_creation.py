#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant
from apps.stores.models import Store, StoreUserMap
from apps.products.models import Product, Category

User = get_user_model()

def test_store_creation():
    print("Testing store-based product and category creation...")
    
    # Create test client
    client = Client()
    client.defaults['HTTP_HOST'] = 'localhost'
    
    # Create test tenant
    tenant, created = Tenant.objects.get_or_create(
        slug='test-tenant',
        defaults={
            'name': 'Test Tenant',
            'description': 'Test tenant for store creation testing'
        }
    )
    print(f"Tenant: {tenant.name} (ID: {tenant.id})")
    
    # Create test store
    store, created = Store.objects.get_or_create(
        name='Test Store',
        tenant=tenant,
        defaults={
            'address': 'Test Address',
            'phone': '1234567890',
            'email': 'test@store.com'
        }
    )
    print(f"Store: {store.name} (ID: {store.id})")
    
    # Create test user (store manager)
    user, created = User.objects.get_or_create(
        username='test_manager',
        defaults={
            'email': 'manager@test.com',
            'first_name': 'Test',
            'last_name': 'Manager',
            'role': 'manager',
            'tenant': tenant
        }
    )
    print(f"User: {user.username} (ID: {user.id}, Role: {user.role})")
    
    # Create store-user mapping
    store_user_map, created = StoreUserMap.objects.get_or_create(
        user=user,
        store=store,
        role='manager',
        defaults={
            'can_view_all': True
        }
    )
    print(f"Store-User Map: User {user.id} -> Store {store.id} (Role: {store_user_map.role})")
    
    # Simulate authentication by setting user in session
    client.force_login(user)
    
    # Test category creation
    print("\n--- Testing Category Creation ---")
    category_data = {
        'name': 'Test Category',
        'description': 'Test category description',
        'store': store.id
    }
    
    response = client.post('/api/products/categories/create/', 
                          data=category_data,
                          content_type='application/json')
    
    print(f"Category creation response status: {response.status_code}")
    if hasattr(response, 'data'):
        print(f"Category creation response data: {response.data}")
    else:
        print(f"Category creation response content: {response.content.decode()}")
    
    # Test product creation
    print("\n--- Testing Product Creation ---")
    product_data = {
        'name': 'Test Product',
        'sku': 'TEST-SKU-001',
        'description': 'Test product description',
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
        'store': store.id
    }
    
    response = client.post('/api/products/create/', 
                          data=product_data,
                          content_type='application/json')
    
    print(f"Product creation response status: {response.status_code}")
    if hasattr(response, 'data'):
        print(f"Product creation response data: {response.data}")
    else:
        print(f"Product creation response content: {response.content.decode()}")
    
    # Test fetching products with scope
    print("\n--- Testing Product Fetching with Scope ---")
    response = client.get('/api/products/?scope=store')
    
    print(f"Product fetching response status: {response.status_code}")
    if hasattr(response, 'data'):
        print(f"Product fetching response data: {response.data}")
    else:
        print(f"Product fetching response content: {response.content.decode()}")
    
    # Test fetching categories with scope
    print("\n--- Testing Category Fetching with Scope ---")
    response = client.get('/api/products/categories/?scope=store')
    
    print(f"Category fetching response status: {response.status_code}")
    if hasattr(response, 'data'):
        print(f"Category fetching response data: {response.data}")
    else:
        print(f"Category fetching response content: {response.content.decode()}")
    
    print("\n--- Test Complete ---")

if __name__ == '__main__':
    test_store_creation() 