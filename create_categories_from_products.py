#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.products.models import Product, Category
from apps.stores.models import Store
from apps.tenants.models import Tenant

def create_categories_from_products():
    print("Creating categories based on existing products...")
    
    # Get Mandeep Jewelries tenant
    tenant = Tenant.objects.filter(name__icontains='mandeep').first()
    if not tenant:
        print("Mandeep Jewelries tenant not found!")
        return
    
    print(f"Tenant: {tenant.name}")
    
    # Get both stores
    stores = Store.objects.filter(tenant=tenant)
    print(f"Found {stores.count()} stores:")
    for store in stores:
        print(f"  - {store.name} (ID: {store.id})")
    
    # Analyze products and create categories for each store
    for store in stores:
        print(f"\n--- Processing Store: {store.name} ---")
        
        # Get products for this store
        products = Product.objects.filter(store=store)
        print(f"Found {products.count()} products in this store")
        
        if products.count() == 0:
            print("No products found in this store, skipping...")
            continue
        
        # Analyze product characteristics to create categories
        categories_to_create = []
        
        # Analyze by material
        materials = products.values_list('material', flat=True).distinct()
        for material in materials:
            if material and material.strip():
                category_name = f"{material.strip()} Jewelry"
                category_description = f"Jewelry made from {material.strip()}"
                categories_to_create.append({
                    'name': category_name,
                    'description': category_description,
                    'store': store,
                    'scope': 'store',
                    'tenant': tenant
                })
        
        # Analyze by type (based on name patterns)
        product_names = products.values_list('name', flat=True)
        jewelry_types = set()
        
        for name in product_names:
            name_lower = name.lower()
            if 'ring' in name_lower:
                jewelry_types.add('Rings')
            elif 'necklace' in name_lower or 'chain' in name_lower:
                jewelry_types.add('Necklaces & Chains')
            elif 'earring' in name_lower:
                jewelry_types.add('Earrings')
            elif 'bracelet' in name_lower or 'bangle' in name_lower:
                jewelry_types.add('Bracelets & Bangles')
            elif 'pendant' in name_lower:
                jewelry_types.add('Pendants')
            elif 'anklet' in name_lower:
                jewelry_types.add('Anklets')
            elif 'set' in name_lower:
                jewelry_types.add('Jewelry Sets')
        
        # Create jewelry type categories
        for jewelry_type in jewelry_types:
            category_name = jewelry_type
            category_description = f"Beautiful {jewelry_type.lower()} collection"
            categories_to_create.append({
                'name': category_name,
                'description': category_description,
                'store': store,
                'scope': 'store',
                'tenant': tenant
            })
        
        # Analyze by price range
        prices = products.values_list('selling_price', flat=True)
        if prices:
            min_price = min(prices)
            max_price = max(prices)
            
            if max_price > 0:
                # Create price-based categories
                if max_price <= 5000:
                    categories_to_create.append({
                        'name': 'Budget Collection',
                        'description': 'Affordable jewelry under ₹5,000',
                        'store': store,
                        'scope': 'store',
                        'tenant': tenant
                    })
                
                if max_price >= 10000:
                    categories_to_create.append({
                        'name': 'Premium Collection',
                        'description': 'High-end jewelry above ₹10,000',
                        'store': store,
                        'scope': 'store',
                        'tenant': tenant
                    })
                
                if min_price >= 5000 and max_price <= 15000:
                    categories_to_create.append({
                        'name': 'Mid-Range Collection',
                        'description': 'Quality jewelry between ₹5,000 - ₹15,000',
                        'store': store,
                        'scope': 'store',
                        'tenant': tenant
                    })
        
        # Create categories
        created_categories = []
        for category_data in categories_to_create:
            # Check if category already exists
            existing_category = Category.objects.filter(
                name=category_data['name'],
                store=store,
                tenant=tenant
            ).first()
            
            if not existing_category:
                category = Category.objects.create(**category_data)
                created_categories.append(category)
                print(f"  Created category: {category.name}")
            else:
                print(f"  Category already exists: {existing_category.name}")
        
        print(f"Created {len(created_categories)} new categories for {store.name}")
        
        # Assign products to categories
        print(f"\nAssigning products to categories...")
        for product in products:
            # Find the best matching category
            best_category = None
            
            # Try to match by material first
            if product.material:
                material_category = Category.objects.filter(
                    name__icontains=product.material,
                    store=store
                ).first()
                if material_category:
                    best_category = material_category
            
            # If no material match, try jewelry type
            if not best_category:
                product_name_lower = product.name.lower()
                if 'ring' in product_name_lower:
                    best_category = Category.objects.filter(name='Rings', store=store).first()
                elif 'necklace' in product_name_lower or 'chain' in product_name_lower:
                    best_category = Category.objects.filter(name='Necklaces & Chains', store=store).first()
                elif 'earring' in product_name_lower:
                    best_category = Category.objects.filter(name='Earrings', store=store).first()
                elif 'bracelet' in product_name_lower or 'bangle' in product_name_lower:
                    best_category = Category.objects.filter(name='Bracelets & Bangles', store=store).first()
                elif 'pendant' in product_name_lower:
                    best_category = Category.objects.filter(name='Pendants', store=store).first()
                elif 'anklet' in product_name_lower:
                    best_category = Category.objects.filter(name='Anklets', store=store).first()
                elif 'set' in product_name_lower:
                    best_category = Category.objects.filter(name='Jewelry Sets', store=store).first()
            
            # If still no match, assign to first available category
            if not best_category:
                best_category = Category.objects.filter(store=store).first()
            
            if best_category:
                product.category = best_category
                product.save()
                print(f"  Assigned '{product.name}' to category '{best_category.name}'")
            else:
                print(f"  No category found for product: {product.name}")
    
    print("\n--- Category Creation Complete ---")
    
    # Summary
    for store in stores:
        categories = Category.objects.filter(store=store)
        products = Product.objects.filter(store=store)
        print(f"\n{store.name}:")
        print(f"  Categories: {categories.count()}")
        print(f"  Products: {products.count()}")
        for category in categories:
            product_count = category.products.count()
            print(f"    - {category.name}: {product_count} products")

if __name__ == '__main__':
    create_categories_from_products() 