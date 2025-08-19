#!/usr/bin/env python
import os
import django
import requests

# Setup Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User
from rest_framework_simplejwt.tokens import RefreshToken

def get_user_token(username):
    """Get JWT token for a user"""
    try:
        user = User.objects.get(username=username)
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    except User.DoesNotExist:
        print(f"User {username} not found")
        return None

def test_middleware_in_request():
    """Test if middleware is working in actual requests"""
    
    print("=== Testing Middleware in Actual Requests ===")
    
    # Test Mani
    print("\n--- Testing Mani ---")
    mani_token = get_user_token('mani')
    if mani_token:
        headers = {'Authorization': f'Bearer {mani_token}'}
        response = requests.get('http://localhost:8000/api/sales/pipeline/', headers=headers)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            pipelines = data.get('results', [])
            print(f"Received {len(pipelines)} pipelines")
            
            # Check if filtering is working
            mani_pipelines = [p for p in pipelines if p.get('sales_representative', {}).get('username') == 'mani']
            print(f"Pipelines assigned to mani: {len(mani_pipelines)}")
            
            if len(mani_pipelines) == len(pipelines):
                print("✅ SUCCESS: Mani only sees his own pipelines!")
            else:
                print("❌ FAILURE: Mani can see other people's pipelines!")
    
    # Test Das
    print("\n--- Testing Das ---")
    das_token = get_user_token('das')
    if das_token:
        headers = {'Authorization': f'Bearer {das_token}'}
        response = requests.get('http://localhost:8000/api/sales/pipeline/', headers=headers)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            pipelines = data.get('results', [])
            print(f"Received {len(pipelines)} pipelines")
            
            # Check if filtering is working
            das_pipelines = [p for p in pipelines if p.get('sales_representative', {}).get('username') == 'das']
            print(f"Pipelines assigned to das: {len(das_pipelines)}")
            
            if len(das_pipelines) == len(pipelines):
                print("✅ SUCCESS: Das only sees his own pipelines!")
            else:
                print("❌ FAILURE: Das can see other people's pipelines!")
                print(f"Expected: {len(das_pipelines)}, Got: {len(pipelines)}")

if __name__ == "__main__":
    test_middleware_in_request() 