#!/usr/bin/env python
"""
Test script to check if the API endpoints are working correctly
"""
import os
import sys
import django
from django.conf import settings

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import User
from apps.tenants.models import Tenant
from apps.stores.models import Store

def test_api_endpoints():
    """Test the API endpoints"""
    print("Testing API endpoints...")
    
    # Create a test client
    client = APIClient()
    
    # Set the test server host
    client.defaults['HTTP_HOST'] = 'localhost'
    
    # Get or create a test user
    try:
        user = User.objects.get(username='testuser')
    except User.DoesNotExist:
        # Create a test user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='manager'
        )
    
    # Get or create a test tenant
    try:
        tenant = Tenant.objects.get(name='Test Tenant')
    except Tenant.DoesNotExist:
        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            address='Test Address',
            phone='1234567890',
            email='test@tenant.com'
        )
    
    # Get or create a test store
    try:
        store = Store.objects.get(name='Test Store')
    except Store.DoesNotExist:
        store = Store.objects.create(
            name='Test Store',
            code='test-store',
            address='Test Store Address',
            city='Test City',
            state='Test State',
            timezone='UTC',
            tenant=tenant
        )
    
    # Assign user to store
    user.store = store
    user.tenant = tenant
    user.save()
    
    # Authenticate the client
    client.force_authenticate(user=user)
    
    # Set the user in the request
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer test_token'
    
    # Test categories endpoint
    print("\n1. Testing categories endpoint...")
    response = client.get('/api/products/categories/')
    print(f"   Status: {response.status_code}")
    if hasattr(response, 'data'):
        print(f"   Response: {response.data}")
    else:
        print(f"   Response: {response.content}")
    
    # Test category creation
    print("\n2. Testing category creation...")
    category_data = {
        'name': 'Test Category',
        'description': 'Test category description',
        'is_active': True,
        'store': store.id
    }
    response = client.post('/api/products/categories/create/', category_data, format='json')
    print(f"   Status: {response.status_code}")
    if hasattr(response, 'data'):
        print(f"   Response: {response.data}")
    else:
        print(f"   Response: {response.content}")
    
    if response.status_code == status.HTTP_201_CREATED:
        category_id = response.data['id']
        
        # Test category update
        print("\n3. Testing category update...")
        update_data = {
            'name': 'Updated Test Category',
            'description': 'Updated description'
        }
        response = client.put(f'/api/products/categories/{category_id}/update/', update_data, format='json')
        print(f"   Status: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"   Response: {response.data}")
        else:
            print(f"   Response: {response.content}")
        
        # Test category deletion
        print("\n4. Testing category deletion...")
        response = client.delete(f'/api/products/categories/{category_id}/delete/')
        print(f"   Status: {response.status_code}")
    
    # Test products endpoint
    print("\n5. Testing products endpoint...")
    response = client.get('/api/products/list/')
    print(f"   Status: {response.status_code}")
    if hasattr(response, 'data'):
        print(f"   Response: {response.data}")
    else:
        print(f"   Response: {response.content}")
    
    print("\nAPI endpoint testing completed!")

if __name__ == '__main__':
    test_api_endpoints() 