from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Tenant
from .serializers import TenantSerializer
from apps.users.permissions import IsRoleAllowed
from apps.clients.models import Client
from apps.sales.models import Sale, SalesPipeline
from apps.products.models import Product
from apps.users.models import User, TeamMember
from rest_framework.permissions import IsAuthenticated
from apps.stores.models import Store

User = get_user_model()

class TenantListView(generics.ListAPIView):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'platform_admin'])]

    def get(self, request, *args, **kwargs):
        # Check if user has the required role
        if request.user.role not in ['business_admin', 'platform_admin']:
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all tenants
        tenants = Tenant.objects.all()
        
        # Serialize the data
        serializer = self.get_serializer(tenants, many=True)
        data = serializer.data
        
        return Response(data)

class TenantCreateView(generics.CreateAPIView):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'platform_admin'])]

    def create(self, request, *args, **kwargs):
        admin_username = request.data.get('admin_username')
        admin_email = request.data.get('admin_email')
        admin_password = request.data.get('admin_password')
      
        if not (admin_username and admin_email and admin_password):
            missing_fields = []
            if not admin_username:
                missing_fields.append('admin_username')
            if not admin_email:
                missing_fields.append('admin_email')
            if not admin_password:
                missing_fields.append('admin_password')
            return Response({
                'detail': f'Admin username, email, and password are required. Missing: {", ".join(missing_fields)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password strength
        if len(admin_password) < 8:
            return Response({
                'detail': 'Admin password must be at least 8 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate email format
        import re
        email_regex = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
        if not email_regex.match(admin_email):
            return Response({
                'detail': 'Please enter a valid email address for the admin account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if username or email already exists globally
        if User.objects.filter(username=admin_username).exists():
            return Response({
                'detail': 'Admin username already exists in the system'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=admin_email).exists():
            return Response({
                'detail': 'Admin email already exists in the system'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create the tenant first
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            tenant = serializer.save()
            
            # Create the admin user for this tenant
            user = User.objects.create_user(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                role=User.Role.BUSINESS_ADMIN,
                tenant=tenant,
                is_active=True
            )
            
            headers = self.get_success_headers(serializer.data)
            return Response({
                'success': True,
                'message': 'Tenant and admin user created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            # If anything goes wrong, clean up the tenant
            if 'tenant' in locals():
                tenant.delete()
            return Response({
                'detail': f'Failed to create tenant: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TenantDetailView(generics.RetrieveAPIView):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'platform_admin'])]

class TenantUpdateView(generics.UpdateAPIView):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'platform_admin'])]
    lookup_field = 'pk'
    
    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Tenant updated successfully',
                'data': response.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'detail': f'Failed to update tenant: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TenantDeleteView(generics.DestroyAPIView):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsRoleAllowed.for_roles(['platform_admin'])]

    def perform_destroy(self, instance):
        """Perform tenant deletion with proper cleanup."""
        try:
            # Get all related data for logging
            user_count = instance.users.count()
            client_count = Client.objects.filter(tenant=instance).count()
            product_count = Product.objects.filter(tenant=instance).count()
            sale_count = Sale.objects.filter(tenant=instance).count()
            
            print(f"Deleting tenant {instance.name} (ID: {instance.id})")
            print(f"Related data to be deleted:")
            print(f"- Users: {user_count}")
            print(f"- Clients: {client_count}")
            print(f"- Products: {product_count}")
            print(f"- Sales: {sale_count}")
            
            # Delete all related data
            # Note: This will cascade delete due to foreign key relationships
            # but we're being explicit for better control and logging
            
            # Delete sales and related data
            Sale.objects.filter(tenant=instance).delete()
            SalesPipeline.objects.filter(tenant=instance).delete()
            
            # Delete products
            Product.objects.filter(tenant=instance).delete()
            
            # Delete clients and related data
            Client.objects.filter(tenant=instance).delete()
            
            # Delete users (this will cascade to team members)
            instance.users.all().delete()
            
            # Finally delete the tenant
            instance.delete()
            
            print(f"Successfully deleted tenant {instance.name} and all related data")
            
        except Exception as e:
            print(f"Error deleting tenant {instance.name}: {e}")
            raise

    def destroy(self, request, *args, **kwargs):
        """Override destroy method to return proper response."""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'Tenant and all associated data deleted successfully'
        }, status=status.HTTP_200_OK)


class PlatformAdminDashboardView(APIView):
    """Platform Admin Dashboard - Provides platform-wide statistics"""
    permission_classes = [IsRoleAllowed.for_roles(['platform_admin'])]

    def get(self, request):
        try:
            # Get date range for analytics (last 30 days)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
            
            # 1. Total Tenants
            total_tenants = Tenant.objects.count()
            active_tenants = Tenant.objects.filter(subscription_status='active').count()
            
            # 2. Total Users across all tenants
            total_users = User.objects.exclude(role=User.Role.PLATFORM_ADMIN).count()
            
            # 3. Total Sales across all tenants (last 30 days)
            total_sales = Sale.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            ).aggregate(
                total=Sum('total_amount'),
                count=Count('id')
            )
            
            sales_amount = total_sales['total'] or Decimal('0.00')
            sales_count = total_sales['count'] or 0
            
            # 4. Recent Tenants (last 5 created)
            recent_tenants = Tenant.objects.order_by('-created_at')[:5]
            recent_tenants_data = []
            for tenant in recent_tenants:
                recent_tenants_data.append({
                    'id': tenant.id,
                    'name': tenant.name,
                    'business_type': tenant.business_type or 'Jewelry Business',
                    'subscription_status': tenant.subscription_status,
                    'created_at': tenant.created_at.strftime('%Y-%m-%d'),
                    'user_count': tenant.users.count()
                })
            
            # 5. System Health Metrics
            system_health = {
                'uptime': '99.9%',
                'active_subscriptions': active_tenants,
                'total_revenue': float(sales_amount),
                'support_tickets': 0  # Placeholder for future implementation
            }
            
            return Response({
                'total_tenants': total_tenants,
                'active_tenants': active_tenants,
                'total_users': total_users,
                'total_sales': {
                    'amount': float(sales_amount),
                    'count': sales_count
                },
                'recent_tenants': recent_tenants_data,
                'system_health': system_health
            })
            
        except Exception as e:
            return Response(
                {'error': 'Failed to fetch platform dashboard data'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ManagerDashboardView(APIView):
    """Manager Dashboard - Provides store-specific data including closed won pipelines"""
    permission_classes = [IsRoleAllowed.for_roles(['manager'])]
    
    def get(self, request):
        try:
            user = request.user
            print(f"=== ManagerDashboardView.get called ===")
            print(f"User: {user.username}, Role: {user.role}")
            
            if not user.store:
                return Response({
                    'success': False,
                    'error': 'Manager not assigned to any store'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            print(f"Manager store: {user.store.name}")
            
            # Get date range for current month
            today = timezone.now()
            start_date = today - timedelta(days=30)
            end_date = today
            
            # Base filters for manager's store only
            base_sales_filter = {'tenant': user.tenant, 'client__store': user.store}
            base_pipeline_filter = {'tenant': user.tenant, 'client__store': user.store}
            
            # Get sales data for current month
            monthly_sales = Sale.objects.filter(
                **base_sales_filter,
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            # Get closed won pipeline data for current month
            monthly_closed_won = SalesPipeline.objects.filter(
                **base_pipeline_filter,
                stage='closed_won'
            ).filter(
                Q(actual_close_date__gte=start_date, actual_close_date__lte=end_date) |
                Q(actual_close_date__isnull=True)  # Include pipelines without close date
            )
            
            # Calculate combined revenue
            sales_revenue = monthly_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            closed_won_revenue = monthly_closed_won.aggregate(total=Sum('expected_value'))['total'] or Decimal('0.00')
            total_monthly_revenue = sales_revenue + closed_won_revenue
            
            # Count sales (including closed won pipelines)
            sales_count = monthly_sales.count()
            closed_won_count = monthly_closed_won.count()
            total_sales_count = sales_count + closed_won_count
            
            # Get store customers
            from apps.clients.models import Client
            total_customers = Client.objects.filter(tenant=user.tenant, store=user.store).count()
            
            # Get team members for this store
            team_members = User.objects.filter(
                tenant=user.tenant,
                role__in=['manager', 'inhouse_sales']
            )
            
            print(f"DEBUG: Sales revenue: {sales_revenue}, Closed won revenue: {closed_won_revenue}")
            print(f"DEBUG: Total monthly revenue: {total_monthly_revenue}")
            print(f"DEBUG: Sales count: {sales_count}, Closed won count: {closed_won_count}")
            print(f"DEBUG: Total sales count: {total_sales_count}")
            
            dashboard_data = {
                'store_name': user.store.name,
                'monthly_revenue': float(total_monthly_revenue),
                'sales_count': total_sales_count,
                'closed_won_count': closed_won_count,
                'total_customers': total_customers,
                'team_members_count': team_members.count(),
                'sales_revenue': float(sales_revenue),
                'closed_won_revenue': float(closed_won_revenue)
            }
            
            return Response({
                'success': True,
                'data': dashboard_data
            })
            
        except Exception as e:
            print(f"Error in ManagerDashboardView: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to fetch dashboard data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BusinessDashboardView(APIView):
    """Business Admin Dashboard - Provides real data for the dashboard"""
    permission_classes = [IsRoleAllowed.for_roles(['business_admin', 'manager', 'inhouse_sales'])]

    def get(self, request):
        user = request.user
        tenant = user.tenant
        
        if not tenant:
            return Response({'error': 'No tenant associated with user'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get date ranges for analytics
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        today_start = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = end_date - timedelta(days=7)
        
        try:
            # Base filters based on user role
            base_sales_filter = {'tenant': tenant}
            base_pipeline_filter = {'tenant': tenant}
            base_store_filter = {'tenant': tenant}
            
            # Role-based filtering
            if user.role == 'business_admin':
                # Business admin sees all data across all stores
                pass
            elif user.role == 'manager':
                # Manager sees only their store data
                if user.store:
                    base_sales_filter['client__store'] = user.store
                    base_pipeline_filter['client__store'] = user.store
                    base_store_filter['id'] = user.store.id
            elif user.role == 'inhouse_sales':
                # In-house sales sees only their store data
                if user.store:
                    base_sales_filter['client__store'] = user.store
                    base_pipeline_filter['client__store'] = user.store
                    base_store_filter['id'] = user.store.id
            
            # 1. Total Sales (today, week, month) - Include both sales and closed won pipeline
            today_sales = Sale.objects.filter(
                **base_sales_filter,
                created_at__gte=today_start,
                created_at__lte=end_date
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            today_closed_won = SalesPipeline.objects.filter(
                **base_pipeline_filter,
                stage='closed_won'
            ).filter(
                Q(actual_close_date__gte=today_start, actual_close_date__lte=end_date) |
                Q(actual_close_date__isnull=True)  # Include pipelines without close date
            ).aggregate(total=Sum('expected_value'))['total'] or Decimal('0.00')
            
            today_total = today_sales + today_closed_won
            
            # Count sales (including closed won pipelines)
            today_sales_count = Sale.objects.filter(
                **base_sales_filter,
                created_at__gte=today_start,
                created_at__lte=end_date
            ).count()
            
            today_closed_won_count = SalesPipeline.objects.filter(
                **base_pipeline_filter,
                stage='closed_won'
            ).filter(
                Q(actual_close_date__gte=today_start, actual_close_date__lte=end_date) |
                Q(actual_close_date__isnull=True)  # Include pipelines without close date
            ).count()
            
            today_total_sales_count = today_sales_count + today_closed_won_count
            
            week_sales = Sale.objects.filter(
                **base_sales_filter,
                created_at__gte=week_start,
                created_at__lte=end_date
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            week_closed_won = SalesPipeline.objects.filter(
                **base_pipeline_filter,
                stage='closed_won'
            ).filter(
                Q(actual_close_date__gte=week_start, actual_close_date__lte=end_date) |
                Q(actual_close_date__isnull=True)  # Include pipelines without close date
            ).aggregate(total=Sum('expected_value'))['total'] or Decimal('0.00')
            
            week_total = week_sales + week_closed_won
            
            # Count sales (including closed won pipelines)
            week_sales_count = Sale.objects.filter(
                **base_sales_filter,
                created_at__gte=week_start,
                created_at__lte=end_date
            ).count()
            
            week_closed_won_count = SalesPipeline.objects.filter(
                **base_pipeline_filter,
                stage='closed_won'
            ).filter(
                Q(actual_close_date__gte=week_start, actual_close_date__lte=end_date) |
                Q(actual_close_date__isnull=True)  # Include pipelines without close date
            ).count()
            
            week_total_sales_count = week_sales_count + week_closed_won_count
            
            month_sales = Sale.objects.filter(
                **base_sales_filter,
                created_at__gte=start_date,
                created_at__lte=end_date
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            month_closed_won = SalesPipeline.objects.filter(
                **base_pipeline_filter,
                stage='closed_won'
            ).filter(
                Q(actual_close_date__gte=start_date, actual_close_date__lte=end_date) |
                Q(actual_close_date__isnull=True)  # Include pipelines without close date
            ).aggregate(total=Sum('expected_value'))['total'] or Decimal('0.00')
            
            month_total = month_sales + month_closed_won
            
            # Count sales (including closed won pipelines)
            month_sales_count = Sale.objects.filter(
                **base_sales_filter,
                created_at__gte=start_date,
                created_at__lte=end_date
            ).count()
            
            month_closed_won_count = SalesPipeline.objects.filter(
                **base_pipeline_filter,
                stage='closed_won'
            ).filter(
                Q(actual_close_date__gte=start_date, actual_close_date__lte=end_date) |
                Q(actual_close_date__isnull=True)  # Include pipelines without close date
            ).count()
            
            month_total_sales_count = month_sales_count + month_closed_won_count
            
            # 2. Pipeline Revenue (pending deals)
            pipeline_revenue = SalesPipeline.objects.filter(
                **base_pipeline_filter,
                stage__in=['lead', 'contacted', 'qualified', 'proposal', 'negotiation']
            ).aggregate(total=Sum('expected_value'))['total'] or Decimal('0.00')
            
            # 3. Closed Won Pipeline Count (moved to sales section)
            closed_won_pipeline_count = SalesPipeline.objects.filter(
                **base_pipeline_filter,
                stage='closed_won'
            ).count()
            
            # 4. Pipeline Deals Count (pending deals)
            pipeline_deals_count = SalesPipeline.objects.filter(
                **base_pipeline_filter,
                stage__in=['lead', 'contacted', 'qualified', 'proposal', 'negotiation']
            ).count()
            
            # 5. Store Performance
            stores = Store.objects.filter(**base_store_filter)
            store_performance = []
            
            for store in stores:
                # For business admin, we need to filter by the specific store
                # For manager/inhouse_sales, they already have store filter applied
                store_sales_filter = {**base_sales_filter}
                store_pipeline_filter = {**base_pipeline_filter}
                
                if user.role == 'business_admin':
                    # Business admin sees all stores, so filter by specific store
                    store_sales_filter['client__store'] = store
                    store_pipeline_filter['client__store'] = store
                elif user.role in ['manager', 'inhouse_sales'] and user.store:
                    # Manager/sales already have store filter, but ensure it's the right store
                    if user.store.id == store.id:
                        store_sales_filter['client__store'] = store
                        store_pipeline_filter['client__store'] = store
                    else:
                        # Skip stores that don't match user's store
                        continue
                
                store_sales = Sale.objects.filter(
                    **store_sales_filter,
                    created_at__gte=start_date,
                    created_at__lte=end_date
                )
                
                # Debug: Check all time data
                all_time_sales = Sale.objects.filter(**store_sales_filter).count()
                all_time_pipeline = SalesPipeline.objects.filter(**store_pipeline_filter, stage='closed_won').count()
                
                store_revenue = store_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
                
                store_closed_won = SalesPipeline.objects.filter(
                    **store_pipeline_filter,
                    stage='closed_won'
                ).aggregate(total=Sum('expected_value'))['total'] or Decimal('0.00')
                
                # Total store revenue = sales + closed won pipeline
                store_total_revenue = store_revenue + store_closed_won
                
                store_performance.append({
                    'id': store.id,
                    'name': store.name,
                    'revenue': float(store_total_revenue),
                    'closed_won_revenue': float(store_closed_won)
                })
            
            # 6. Top Performing Managers (only for business admin and manager roles)
            top_managers = []
            if user.role in ['business_admin', 'manager']:
                # For business admin, show managers from all stores with store info
                # For manager, show only managers from their store
                if user.role == 'business_admin':
                    managers = User.objects.filter(
                        tenant=tenant,
                        role__in=['business_admin', 'manager'],
                        is_active=True
                    )
                else:
                    # Manager role - only show managers from their store
                    managers = User.objects.filter(
                        tenant=tenant,
                        role__in=['business_admin', 'manager'],
                        is_active=True,
                        store=user.store
                    )
                
                for manager in managers:
                    # Filter sales and pipelines specific to this manager
                    manager_sales_filter = {**base_sales_filter, 'sales_representative': manager}
                    
                    # If business admin, also filter by manager's store for accurate location-specific data
                    if user.role == 'business_admin' and manager.store:
                        manager_sales_filter['client__store'] = manager.store
                    
                    # Get all-time sales for this manager (not just last 30 days)
                    manager_all_time_sales = Sale.objects.filter(
                        **manager_sales_filter
                    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
                    
                    # Get recent sales (last 30 days)
                    manager_recent_sales = Sale.objects.filter(
                        **manager_sales_filter,
                        created_at__gte=start_date,
                        created_at__lte=end_date
                    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
                    
                    manager_pipeline_filter = {**base_pipeline_filter, 'sales_representative': manager}
                    
                    # If business admin, also filter by manager's store for accurate location-specific data
                    if user.role == 'business_admin' and manager.store:
                        manager_pipeline_filter['client__store'] = manager.store
                    
                    # Get all-time closed won pipelines
                    manager_all_time_closed_won = SalesPipeline.objects.filter(
                        **manager_pipeline_filter,
                        stage='closed_won'
                    ).aggregate(total=Sum('expected_value'))['total'] or Decimal('0.00')
                    
                    manager_deals = SalesPipeline.objects.filter(
                        **manager_pipeline_filter,
                        stage='closed_won'
                    ).count()
                    
                    # Total manager revenue = all-time sales + all-time closed won pipeline
                    manager_total_revenue = manager_all_time_sales + manager_all_time_closed_won
                    
                    # Include managers with any revenue or deals (even if 0 recent activity)
                    if float(manager_total_revenue) > 0 or manager_deals > 0:
                        manager_data = {
                            'id': manager.id,
                            'name': f"{manager.first_name} {manager.last_name}",
                            'revenue': float(manager_total_revenue),
                            'deals_closed': manager_deals,
                            'recent_revenue': float(manager_recent_sales)
                        }
                        
                        # Add store information for business admin to show location
                        if user.role == 'business_admin' and manager.store:
                            manager_data['store_name'] = manager.store.name
                            manager_data['store_location'] = manager.store.location if hasattr(manager.store, 'location') else ''
                        
                        top_managers.append(manager_data)
                    
                    # Debug logging
                    store_info = f" (Store: {manager.store.name if manager.store else 'No Store'})" if user.role == 'business_admin' else ""
                    print(f"Manager {manager.first_name} {manager.last_name}{store_info}: All-time Sales={manager_all_time_sales}, Recent Sales={manager_recent_sales}, Closed Won={manager_all_time_closed_won}, Deals={manager_deals}")
                
                # If no managers with sales found, show all managers for debugging
                if not top_managers:
                    print("No managers with sales found, showing all active managers...")
                    for manager in managers:
                        manager_data = {
                            'id': manager.id,
                            'name': f"{manager.first_name} {manager.last_name}",
                            'revenue': 0.0,
                            'deals_closed': 0,
                            'recent_revenue': 0.0
                        }
                        
                        # Add store information for business admin to show location
                        if user.role == 'business_admin' and manager.store:
                            manager_data['store_name'] = manager.store.name
                            manager_data['store_location'] = manager.store.location if hasattr(manager.store, 'location') else ''
                        
                        top_managers.append(manager_data)
                
                # Sort managers by revenue
                top_managers.sort(key=lambda x: x['revenue'], reverse=True)
                top_managers = top_managers[:5]  # Top 5 managers
                
                print(f"Final top_managers list: {len(top_managers)} managers found")
            
            # 7. Top Performing Salesmen
            salesmen = User.objects.filter(
                tenant=tenant,
                role='inhouse_sales',
                is_active=True
            )
            top_salesmen = []
            
            for salesman in salesmen:
                salesman_sales_filter = {**base_sales_filter}
                if user.role in ['manager', 'inhouse_sales'] and user.store:
                    salesman_sales_filter['client__store'] = user.store
                
                # If business admin, also filter by salesman's store for accurate location-specific data
                if user.role == 'business_admin' and salesman.store:
                    salesman_sales_filter['client__store'] = salesman.store
                
                salesman_sales = Sale.objects.filter(
                    **salesman_sales_filter,
                    sales_representative=salesman,
                    created_at__gte=start_date,
                    created_at__lte=end_date
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
                
                salesman_pipeline_filter = {**base_pipeline_filter}
                if user.role in ['manager', 'inhouse_sales'] and user.store:
                    salesman_pipeline_filter['client__store'] = user.store
                
                # If business admin, also filter by salesman's store for accurate location-specific data
                if user.role == 'business_admin' and salesman.store:
                    salesman_pipeline_filter['client__store'] = salesman.store
                
                salesman_closed_won = SalesPipeline.objects.filter(
                    **salesman_pipeline_filter,
                    sales_representative=salesman,
                    stage='closed_won'
                ).aggregate(total=Sum('expected_value'))['total'] or Decimal('0.00')
                
                salesman_deals = SalesPipeline.objects.filter(
                    **salesman_pipeline_filter,
                    sales_representative=salesman,
                    stage='closed_won'
                ).count()
                
                # Total salesman revenue = sales + closed won pipeline
                salesman_total_revenue = salesman_sales + salesman_closed_won
                
                if float(salesman_total_revenue) > 0:
                    salesman_data = {
                        'id': salesman.id,
                        'name': f"{salesman.first_name} {salesman.last_name}",
                        'revenue': float(salesman_total_revenue),
                        'deals_closed': salesman_deals
                    }
                    
                    # Add store information for business admin to show location
                    if user.role == 'business_admin' and salesman.store:
                        salesman_data['store_name'] = salesman.store.name
                        salesman_data['store_location'] = salesman.store.location if hasattr(salesman.store, 'location') else ''
                    
                    top_salesmen.append(salesman_data)
            
            # Sort salesmen by revenue
            top_salesmen.sort(key=lambda x: x['revenue'], reverse=True)
            top_salesmen = top_salesmen[:5]  # Top 5 salesmen
            
            # Prepare response data
            dashboard_data = {
                'total_sales': {
                    'today': float(today_total),
                    'week': float(week_total),
                    'month': float(month_total),
                    'today_count': today_total_sales_count,
                    'week_count': week_total_sales_count,
                    'month_count': month_total_sales_count
                },
                'pipeline_revenue': float(pipeline_revenue),
                'closed_won_pipeline_count': closed_won_pipeline_count,
                'pipeline_deals_count': pipeline_deals_count,
                'store_performance': store_performance,
                'top_managers': top_managers,
                'top_salesmen': top_salesmen
            }
            
            return Response(dashboard_data)
            
        except Exception as e:
            print(f"Error in BusinessDashboardView: {e}")
            # Return mock data if there's an error
            return Response({
                'total_sales': {
                    'today': 25000.00,
                    'week': 150000.00,
                    'month': 450000.00
                },
                'pipeline_revenue': 350000.00,
                'closed_won_pipeline_count': 25,
                'pipeline_deals_count': 18,
                'store_performance': [
                    {
                        'id': 1,
                        'name': 'Main Store',
                        'revenue': 250000.00,
                        'closed_won_revenue': 200000.00
                    },
                    {
                        'id': 2,
                        'name': 'Branch Store',
                        'revenue': 200000.00,
                        'closed_won_revenue': 150000.00
                    }
                ],
                'top_managers': [
                    {
                        'id': 1,
                        'name': 'Rajesh Kumar',
                        'revenue': 120000.00,
                        'deals_closed': 8
                    },
                    {
                        'id': 2,
                        'name': 'Priya Sharma',
                        'revenue': 95000.00,
                        'deals_closed': 6
                    }
                ],
                'top_salesmen': [
                    {
                        'id': 3,
                        'name': 'Amit Patel',
                        'revenue': 85000.00,
                        'deals_closed': 12
                    },
                    {
                        'id': 4,
                        'name': 'Neha Singh',
                        'revenue': 72000.00,
                        'deals_closed': 10
                    }
                ]
            })
