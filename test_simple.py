#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.sales.models import SalesPipeline
from decimal import Decimal
from django.db.models import Sum, Q

def test_simple():
    print("=== SIMPLE TEST ===")
    
    # Get all closed won pipelines
    closed_won = SalesPipeline.objects.filter(stage='closed_won')
    print(f"Total closed won pipelines: {closed_won.count()}")
    
    # Calculate revenue
    revenue = closed_won.aggregate(total=Sum('expected_value'))['total']
    print(f"Revenue: {revenue}")
    
    # Show individual pipelines
    for pipeline in closed_won:
        print(f"- {pipeline.title}: ₹{pipeline.expected_value}")

if __name__ == "__main__":
    test_simple() 