from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta
from apps.clients.models import Client
from apps.products.models import Product
from apps.sales.models import Sale, SalesPipeline
from apps.users.models import User
from apps.stores.models import Store
from apps.tenants.models import Tenant


@api_view(['GET'])
def dashboard_stats(request):
    """
    Get dashboard statistics using existing data.
    """
    # Get the first tenant or create a default one
    tenant = Tenant.objects.first()
    
    if not tenant:
        return Response({
            'error': 'No tenant found'
        }, status=400)
    
    # Get date range for comparisons (last 30 days vs previous 30 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    previous_start = start_date - timedelta(days=30)
    
    # Current period stats
    current_clients = Client.objects.filter(
        created_at__gte=start_date,
        is_deleted=False
    ).count()
    
    current_sales = Sale.objects.filter(
        created_at__gte=start_date
    ).count()
    
    current_products = Product.objects.filter(
        created_at__gte=start_date
    ).count()
    
    current_revenue = Sale.objects.filter(
        created_at__gte=start_date,
        status__in=['confirmed', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Previous period stats
    previous_clients = Client.objects.filter(
        created_at__gte=previous_start,
        created_at__lt=start_date,
        is_deleted=False
    ).count()
    
    previous_sales = Sale.objects.filter(
        created_at__gte=previous_start,
        created_at__lt=start_date
    ).count()
    
    previous_products = Product.objects.filter(
        created_at__gte=previous_start,
        created_at__lt=start_date
    ).count()
    
    previous_revenue = Sale.objects.filter(
        created_at__gte=previous_start,
        created_at__lt=start_date,
        status__in=['confirmed', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Calculate percentage changes
    def calculate_change(current, previous):
        if previous == 0:
            return '+100%' if current > 0 else '+0%'
        change = ((current - previous) / previous) * 100
        return f"{'+' if change >= 0 else ''}{change:.1f}%"
    
    # Get recent activities
    recent_activities = []
    
    # Recent clients
    recent_clients = Client.objects.filter(
        created_at__gte=end_date - timedelta(days=7),
        is_deleted=False
    ).order_by('-created_at')[:3]
    
    for client in recent_clients:
        recent_activities.append({
            'type': 'customer',
            'message': 'New customer added',
            'details': f"{client.full_name} - {client.created_at.strftime('%b %d, %I:%M %p')}",
            'icon': 'users',
            'timestamp': client.created_at
        })
    
    # Recent sales
    recent_sales = Sale.objects.filter(
        created_at__gte=end_date - timedelta(days=7)
    ).order_by('-created_at')[:3]
    
    for sale in recent_sales:
        recent_activities.append({
            'type': 'sale',
            'message': 'Sale completed',
            'details': f"Order #{sale.order_number} - ₹{sale.total_amount:,.0f} - {sale.created_at.strftime('%b %d, %I:%M %p')}",
            'icon': 'trending',
            'timestamp': sale.created_at
        })
    
    # Recent appointments (if appointments model exists)
    try:
        from apps.clients.models import Appointment
        recent_appointments = Appointment.objects.filter(
            created_at__gte=end_date - timedelta(days=7)
        ).order_by('-created_at')[:3]
        
        for appointment in recent_appointments:
            recent_activities.append({
                'type': 'appointment',
                'message': 'Appointment scheduled',
                'details': f"{appointment.client.full_name} - {appointment.date.strftime('%b %d, %I:%M %p')}",
                'icon': 'calendar',
                'timestamp': appointment.created_at
            })
    except ImportError:
        pass  # Appointments model might not be available
    
    # Sort activities by timestamp
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:5]  # Limit to 5 most recent
    
    # Remove timestamp from response
    for activity in recent_activities:
        activity.pop('timestamp', None)
    
    # Total counts (not just recent)
    total_clients = Client.objects.filter(is_deleted=False).count()
    total_sales = Sale.objects.count()
    total_products = Product.objects.count()
    total_revenue = Sale.objects.filter(
        status__in=['confirmed', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    return Response({
        'total_customers': total_clients,
        'total_sales': total_sales,
        'total_products': total_products,
        'total_revenue': float(total_revenue),
        'customers_change': calculate_change(current_clients, previous_clients),
        'sales_change': calculate_change(current_sales, previous_sales),
        'products_change': calculate_change(current_products, previous_products),
        'revenue_change': calculate_change(current_revenue, previous_revenue),
        'recent_activities': recent_activities
    })


@api_view(['GET'])
def business_admin_dashboard(request):
    """
    Get comprehensive business admin dashboard data.
    """
    tenant = Tenant.objects.first()
    
    if not tenant:
        return Response({
            'error': 'No tenant found'
        }, status=400)
    
    # Date ranges
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    previous_start = start_date - timedelta(days=30)
    
    # Revenue metrics
    current_revenue = Sale.objects.filter(
        created_at__gte=start_date,
        status__in=['confirmed', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    previous_revenue = Sale.objects.filter(
        created_at__gte=previous_start,
        created_at__lt=start_date,
        status__in=['confirmed', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    revenue_growth = 0
    if previous_revenue > 0:
        revenue_growth = ((current_revenue - previous_revenue) / previous_revenue) * 100
    
    # Store performance
    stores = Store.objects.all()
    store_performance = []
    
    for store in stores:
        store_sales = Sale.objects.filter(
            created_at__gte=start_date,
            status__in=['confirmed', 'delivered']
        )
        
        store_revenue = store_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        store_customers = Client.objects.filter(
            created_at__gte=start_date,
            is_deleted=False
        ).count()
        
        store_performance.append({
            'id': store.id,
            'name': store.name,
            'revenue': float(store_revenue),
            'growth': 12.5,  # Mock growth for now
            'customers': store_customers,
            'staff': User.objects.filter(store=store).count(),
            'target': 1000000,  # Mock target
        })
    
    # Team performance
    team_members = User.objects.filter(is_active=True)
    team_performance = []
    
    for member in team_members:
        member_sales = Sale.objects.filter(
            sales_representative=member.id,
            created_at__gte=start_date,
            status__in=['confirmed', 'delivered']
        )
        
        member_revenue = member_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        member_customers = Client.objects.filter(
            assigned_to=member.id,
            created_at__gte=start_date,
            is_deleted=False
        ).count()
        
        team_performance.append({
            'id': member.id,
            'name': member.name,
            'role': member.role,
            'revenue': float(member_revenue),
            'customers': member_customers,
            'sales_count': member_sales.count(),
            'avatar': None,
        })
    
    # E-commerce metrics (mock for now)
    ecommerce_metrics = {
        'orders': 156,
        'revenue': 780000,
        'conversion': 3.2,
        'visitors': 12450,
    }
    
    # Inventory metrics
    inventory_metrics = {
        'products': Product.objects.count(),
        'categories': Product.objects.values('category').distinct().count(),
        'low_stock': Product.objects.filter(quantity__lte=10).count(),
    }
    
    # Customer metrics
    customer_metrics = {
        'total': Client.objects.filter(is_deleted=False).count(),
        'new_this_month': Client.objects.filter(
            created_at__gte=start_date,
            is_deleted=False
        ).count(),
        'retention_rate': 78.5,  # Mock retention rate
    }
    
    return Response({
        'revenue': {
            'total': float(current_revenue),
            'growth': revenue_growth,
            'this_month': float(current_revenue),
            'target': 600000,
        },
        'stores': {
            'total': stores.count(),
            'active': stores.count(),
            'top_performing': store_performance[0]['name'] if store_performance else 'No stores',
        },
        'customers': customer_metrics,
        'ecommerce': ecommerce_metrics,
        'inventory': inventory_metrics,
        'store_performance': store_performance,
        'team_performance': team_performance,
    })


@api_view(['GET'])
def sales_analytics(request):
    """
    Get sales analytics data.
    """
    # Sales by status
    sales_by_status = Sale.objects.values('status').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    )
    
    # Sales by month (last 12 months)
    from django.db.models.functions import TruncMonth
    monthly_sales = Sale.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=365)
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('month')
    
    return Response({
        'sales_by_status': list(sales_by_status),
        'monthly_sales': list(monthly_sales)
    })


@api_view(['GET'])
def customer_analytics(request):
    """
    Get customer analytics data.
    """
    # Customers by source
    customers_by_source = Client.objects.filter(
        is_deleted=False
    ).values('lead_source').annotate(count=Count('id'))
    
    # Customers by status
    customers_by_status = Client.objects.filter(
        is_deleted=False
    ).values('status').annotate(count=Count('id'))
    
    # Recent customer growth
    from django.db.models.functions import TruncDate
    daily_customers = Client.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=30),
        is_deleted=False
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(count=Count('id')).order_by('date')
    
    return Response({
        'customers_by_source': list(customers_by_source),
        'customers_by_status': list(customers_by_status),
        'daily_customers': list(daily_customers)
    })


@api_view(['GET'])
def product_analytics(request):
    """
    Get product analytics data.
    """
    # Products by category
    products_by_category = Product.objects.values(
        'category__name'
    ).annotate(
        count=Count('id'),
        total_value=Sum('selling_price')
    )
    
    # Low stock products
    low_stock_products = Product.objects.filter(
        quantity__lte=models.F('min_quantity')
    ).values('name', 'quantity', 'min_quantity')[:10]
    
    # Top selling products (based on sales)
    from apps.sales.models import SaleItem
    top_products = SaleItem.objects.values(
        'product__name'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_revenue')[:10]
    
    return Response({
        'products_by_category': list(products_by_category),
        'low_stock_products': list(low_stock_products),
        'top_products': list(top_products)
    })
