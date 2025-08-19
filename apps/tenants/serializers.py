from rest_framework import serializers
from .models import Tenant
from apps.users.models import User
from django.utils.text import slugify
import random
import string
import re


class TenantSerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tenant
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_users(self, obj):
        """Get users for this tenant."""
        users = obj.users.all()
        return [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
            }
            for user in users
        ]
    
    def get_user_count(self, obj):
        """Get the number of users for this tenant."""
        return obj.users.count()
    
    def validate_website(self, value):
        """Validate and format website URL."""
        if not value:
            return value
        
        # If URL doesn't start with http:// or https://, add https://
        if value and not value.startswith(('http://', 'https://')):
            value = 'https://' + value
        
        return value
    
    def validate_google_maps_url(self, value):
        """Validate and format Google Maps URL."""
        if not value:
            return value
        
        # If URL doesn't start with http:// or https://, add https://
        if value and not value.startswith(('http://', 'https://')):
            value = 'https://' + value
        
        return value
    
    def to_internal_value(self, data):
        """Convert string numbers to integers for numeric fields and generate slug."""
        data = data.copy()
        
        # Convert string numbers to integers for numeric fields
        if 'max_users' in data and isinstance(data['max_users'], str):
            data['max_users'] = int(data['max_users'])
        if 'max_storage_gb' in data and isinstance(data['max_storage_gb'], str):
            data['max_storage_gb'] = int(data['max_storage_gb'])
        
        # Generate slug if not provided and name is available
        if ('slug' not in data or not data['slug']) and 'name' in data and data['name']:
            data['slug'] = self.generate_unique_slug(data['name'])
        
        return super().to_internal_value(data)
    
    def validate_slug(self, value):
        """Validate that the slug is unique."""
        # Get the current instance if this is an update
        instance = getattr(self, 'instance', None)
        
        # Check if slug exists for other tenants
        queryset = Tenant.objects.filter(slug=value)
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
            
        if queryset.exists():
            raise serializers.ValidationError("A tenant with this slug already exists.")
        return value
    
    def generate_unique_slug(self, name):
        """Generate a unique slug from the tenant name."""
        base_slug = slugify(name)
        slug = base_slug
        
        # Keep trying until we find a unique slug
        counter = 1
        while Tenant.objects.filter(slug=slug).exists():
            # Add a random suffix to make it unique
            random_suffix = ''.join(random.choices(string.digits, k=4))
            slug = f"{base_slug}-{random_suffix}"
            counter += 1
            if counter > 10:  # Prevent infinite loop
                break
        
        return slug
    
    def create(self, validated_data):
        """Create a new tenant with default values."""
        # Set default values if not provided
        if 'subscription_status' not in validated_data:
            validated_data['subscription_status'] = 'active'
        if 'is_active' not in validated_data:
            validated_data['is_active'] = True
        if 'max_users' not in validated_data:
            validated_data['max_users'] = 5
        if 'max_storage_gb' not in validated_data:
            validated_data['max_storage_gb'] = 10
        
        # Generate slug if not provided
        if 'slug' not in validated_data or not validated_data['slug']:
            validated_data['slug'] = self.generate_unique_slug(validated_data['name'])
            
        return super().create(validated_data) 