#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.products.models import Product
from apps.stores.models import Store
from apps.tenants.models import Tenant

def distribute_products():
    """Distribute products between Mandeep Jewelries stores"""
    
    # Find Mandeep Jewelries tenant
    try:
        tenant = Tenant.objects.get(name__icontains='mandeep')
        print(f"Found tenant: {tenant.name}")
    except Tenant.DoesNotExist:
        print("Mandeep Jewelries tenant not found. Available tenants:")
        for t in Tenant.objects.all():
            print(f"  - {t.name}")
        return
    
    # Find the two stores
    stores = Store.objects.filter(tenant=tenant)
    print(f"Found {stores.count()} stores for {tenant.name}:")
    for store in stores:
        print(f"  - {store.name} (ID: {store.id})")
    
    if stores.count() < 2:
        print("Need at least 2 stores to distribute products")
        return
    
    # Get all products for this tenant
    products = Product.objects.filter(tenant=tenant)
    print(f"\nFound {products.count()} products for {tenant.name}")
    
    if products.count() == 0:
        print("No products found to distribute")
        return
    
    # Get the two stores
    store1 = stores[0]
    store2 = stores[1]
    
    print(f"\nDistributing products:")
    print(f"Store 1: {store1.name}")
    print(f"Store 2: {store2.name}")
    
    # Calculate how many products per store
    total_products = products.count()
    products_per_store = total_products // 2
    remainder = total_products % 2
    
    print(f"\nDistribution plan:")
    print(f"  Store 1 ({store1.name}): {products_per_store + remainder} products")
    print(f"  Store 2 ({store2.name}): {products_per_store} products")
    
    # Get products that don't have a store assigned (scope='global' or store=None)
    unassigned_products = products.filter(store__isnull=True)
    print(f"\nFound {unassigned_products.count()} unassigned products")
    
    if unassigned_products.count() == 0:
        print("All products already have stores assigned")
        return
    
    # Distribute products
    product_list = list(unassigned_products)
    
    # Assign first half to store1
    for i in range(products_per_store + remainder):
        if i < len(product_list):
            product = product_list[i]
            product.store = store1
            product.scope = 'store'
            product.save()
            print(f"  Assigned '{product.name}' to {store1.name}")
    
    # Assign second half to store2
    for i in range(products_per_store + remainder, len(product_list)):
        product = product_list[i]
        product.store = store2
        product.scope = 'store'
        product.save()
        print(f"  Assigned '{product.name}' to {store2.name}")
    
    # Verify distribution
    store1_products = Product.objects.filter(tenant=tenant, store=store1)
    store2_products = Product.objects.filter(tenant=tenant, store=store2)
    global_products = Product.objects.filter(tenant=tenant, scope='global')
    
    print(f"\nFinal distribution:")
    print(f"  {store1.name}: {store1_products.count()} products")
    print(f"  {store2.name}: {store2_products.count()} products")
    print(f"  Global products: {global_products.count()} products")
    print(f"  Total: {Product.objects.filter(tenant=tenant).count()} products")

if __name__ == '__main__':
    distribute_products() 