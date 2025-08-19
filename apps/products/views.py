from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta
import csv
import io
from decimal import Decimal

from .models import Product, Category, ProductVariant, ProductInventory, StockTransfer
from .serializers import (
    ProductSerializer, ProductListSerializer, ProductDetailSerializer, 
    CategorySerializer, ProductVariantSerializer, ProductInventorySerializer,
    StockTransferSerializer, StockTransferListSerializer
)
from apps.users.permissions import IsRoleAllowed
from apps.tenants.models import Tenant


class CustomProductPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductListSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager', 'inhouse_sales', 'tele_calling', 'marketing'])]
    pagination_class = CustomProductPagination
    
    def get_queryset(self):
        user = self.request.user
        queryset = Product.objects.filter(tenant=user.tenant)
        
        # Filter by scope first - this overrides role-based filtering
        scope_filter = self.request.query_params.get('scope')
        if scope_filter == 'all':
            # When scope='all' is requested, show all products regardless of role
            pass
        elif scope_filter == 'global':
            queryset = queryset.filter(scope='global')
        elif scope_filter == 'store':
            queryset = queryset.filter(scope='store')
        else:
            # Apply scoped visibility based on user role when no specific scope is requested
            if user.role == 'business_admin':
                # Business admin sees all products (global + store-specific)
                pass
            elif user.role == 'manager':
                # Store manager sees their store products + global products
                queryset = queryset.filter(
                    Q(store=user.store) | Q(scope='global')
                )
            else:
                # Other users see their store products + global products
                queryset = queryset.filter(
                    Q(store=user.store) | Q(scope='global')
                )
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Search by name or SKU
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(sku__icontains=search)
            )
        
        # Filter by stock level
        stock_filter = self.request.query_params.get('stock')
        if stock_filter == 'low':
            queryset = queryset.filter(quantity__lte=F('min_quantity'))
        elif stock_filter == 'out':
            queryset = queryset.filter(quantity=0)
        
        return queryset.order_by('-created_at')


class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    parser_classes = [MultiPartParser, FormParser]
    
    def perform_create(self, serializer):
        # Store and scope are set in serializer.create() method
        serializer.save(tenant=self.request.user.tenant)


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager', 'inhouse_sales', 'tele_calling', 'marketing'])]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Product.objects.filter(tenant=user.tenant)
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            queryset = queryset.filter(
                Q(store=user.store) | Q(scope='global')
            )
        
        return queryset


class ProductUpdateView(generics.UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Product.objects.filter(tenant=user.tenant)
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            queryset = queryset.filter(
                Q(store=user.store) | Q(scope='global')
            )
        
        return queryset


class ProductDeleteView(generics.DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Product.objects.filter(tenant=user.tenant)
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            queryset = queryset.filter(
                Q(store=user.store) | Q(scope='global')
            )
        
        return queryset


class ProductStatsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager', 'inhouse_sales', 'tele_calling', 'marketing'])]
    
    def get(self, request):
        user = request.user
        tenant = user.tenant
        
        # Base queryset with scoped visibility
        if user.role == 'business_admin':
            products_queryset = Product.objects.filter(tenant=tenant)
        else:
            products_queryset = Product.objects.filter(
                tenant=tenant
            ).filter(
                Q(store=user.store) | Q(scope='global')
            )
        
        # Basic stats
        total_products = products_queryset.count()
        active_products = products_queryset.filter(status='active').count()
        out_of_stock = products_queryset.filter(quantity=0).count()
        low_stock = products_queryset.filter(quantity__lte=F('min_quantity')).count()
        
        # Inventory value
        total_value = products_queryset.aggregate(
            total=Sum(F('quantity') * F('cost_price'))
        )['total'] or 0
        
        # Category stats
        if user.role == 'business_admin':
            category_queryset = Category.objects.filter(tenant=tenant)
        else:
            category_queryset = Category.objects.filter(
                tenant=tenant
            ).filter(
                Q(store=user.store) | Q(scope='global')
            )
        category_count = category_queryset.count()
        
        # Recent activity
        recent_products = products_queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        return Response({
            'total_products': total_products,
            'active_products': active_products,
            'out_of_stock': out_of_stock,
            'low_stock': low_stock,
            'total_value': float(total_value),
            'category_count': category_count,
            'recent_products': recent_products,
        })


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager', 'inhouse_sales', 'tele_calling', 'marketing'])]
    pagination_class = None  # Disable pagination for categories
    
    def get_queryset(self):
        user = self.request.user
        queryset = Category.objects.filter(tenant=user.tenant)
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            queryset = queryset.filter(
                Q(store=user.store) | Q(scope='global')
            )
        
        return queryset


class CategoryCreateView(generics.CreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def perform_create(self, serializer):
        # Store and scope are set in serializer.create() method
        serializer.save(tenant=self.request.user.tenant)


class CategoryDetailView(generics.RetrieveAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager', 'inhouse_sales', 'tele_calling', 'marketing'])]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Category.objects.filter(tenant=user.tenant)
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            queryset = queryset.filter(
                Q(store=user.store) | Q(scope='global')
            )
        
        return queryset


class CategoryUpdateView(generics.UpdateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Category.objects.filter(tenant=user.tenant)
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            queryset = queryset.filter(
                Q(store=user.store) | Q(scope='global')
            )
        
        return queryset


class CategoryDeleteView(generics.DestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Category.objects.filter(tenant=user.tenant)
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            queryset = queryset.filter(
                Q(store=user.store) | Q(scope='global')
            )
        
        return queryset


# New Inventory Views
class ProductInventoryListView(generics.ListAPIView):
    serializer_class = ProductInventorySerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    pagination_class = CustomProductPagination
    
    def get_queryset(self):
        user = self.request.user
        queryset = ProductInventory.objects.filter(store__tenant=user.tenant)
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            queryset = queryset.filter(store=user.store)
        
        # Filter by store
        store_id = self.request.query_params.get('store')
        if store_id and user.role == 'business_admin':
            queryset = queryset.filter(store_id=store_id)
        
        # Filter by low stock
        low_stock = self.request.query_params.get('low_stock')
        if low_stock == 'true':
            queryset = queryset.filter(quantity__lte=F('reorder_point'))
        
        # Filter by out of stock
        out_of_stock = self.request.query_params.get('out_of_stock')
        if out_of_stock == 'true':
            queryset = queryset.filter(quantity=0)
        
        return queryset.order_by('-last_updated')


class ProductInventoryUpdateView(generics.UpdateAPIView):
    serializer_class = ProductInventorySerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def get_queryset(self):
        user = self.request.user
        queryset = ProductInventory.objects.filter(store__tenant=user.tenant)
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            queryset = queryset.filter(store=user.store)
        
        return queryset


# New Stock Transfer Views
class StockTransferListView(generics.ListAPIView):
    serializer_class = StockTransferListSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    pagination_class = CustomProductPagination
    
    def get_queryset(self):
        user = self.request.user
        queryset = StockTransfer.objects.filter(
            from_store__tenant=user.tenant
        )
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            # Store managers see transfers involving their store
            queryset = queryset.filter(
                Q(from_store=user.store) | Q(to_store=user.store)
            )
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by store
        store_id = self.request.query_params.get('store')
        if store_id and user.role == 'business_admin':
            queryset = queryset.filter(
                Q(from_store_id=store_id) | Q(to_store_id=store_id)
            )
        
        return queryset.order_by('-created_at')


class StockTransferCreateView(generics.CreateAPIView):
    serializer_class = StockTransferSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def perform_create(self, serializer):
        user = self.request.user
        transfer = serializer.save(requested_by=user)
        
        # Send notification for transfer request
        from .services import StockTransferNotificationService
        StockTransferNotificationService.notify_transfer_request(transfer)
        
        return transfer


class StockTransferDetailView(generics.RetrieveAPIView):
    serializer_class = StockTransferSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def get_queryset(self):
        user = self.request.user
        queryset = StockTransfer.objects.filter(
            from_store__tenant=user.tenant
        )
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            queryset = queryset.filter(
                Q(from_store=user.store) | Q(to_store=user.store)
            )
        
        return queryset


class StockTransferApproveView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def post(self, request, pk):
        try:
            transfer = StockTransfer.objects.get(
                id=pk,
                from_store__tenant=request.user.tenant
            )
            
            # Check permissions - Only the receiving store can approve transfers
            if request.user.role != 'business_admin':
                if transfer.to_store != request.user.store:
                    return Response({
                        'success': False,
                        'message': 'You can only approve transfers to your store'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            transfer.approve(request.user)
            
            # Send notification for transfer approval
            from .services import StockTransferNotificationService
            StockTransferNotificationService.notify_transfer_approved(transfer)
            
            return Response({
                'success': True,
                'message': 'Transfer approved successfully'
            })
            
        except StockTransfer.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Transfer not found'
            }, status=status.HTTP_404_NOT_FOUND)


class StockTransferCompleteView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def post(self, request, pk):
        try:
            transfer = StockTransfer.objects.get(
                id=pk,
                from_store__tenant=request.user.tenant
            )
            
            # Check permissions - Only the sending store can complete transfers
            if request.user.role != 'business_admin':
                if transfer.from_store != request.user.store:
                    return Response({
                        'success': False,
                        'message': 'You can only complete transfers from your store'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            if transfer.status != 'approved':
                return Response({
                    'success': False,
                    'message': 'Transfer must be approved before completion'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            success = transfer.complete()
            if success:
                # Send notification for transfer completion
                from .services import StockTransferNotificationService
                StockTransferNotificationService.notify_transfer_completed(transfer)
                
                return Response({
                    'success': True,
                    'message': 'Transfer completed successfully'
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Insufficient stock for transfer'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except StockTransfer.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Transfer not found'
            }, status=status.HTTP_404_NOT_FOUND)


class StockTransferCancelView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def post(self, request, pk):
        try:
            transfer = StockTransfer.objects.get(
                id=pk,
                from_store__tenant=request.user.tenant
            )
            
            # Check permissions - Only the requesting store can cancel transfers
            if request.user.role != 'business_admin':
                if transfer.from_store != request.user.store:
                    return Response({
                        'success': False,
                        'message': 'You can only cancel transfers from your store'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            transfer.cancel()
            
            # Send notification for transfer cancellation
            from .services import StockTransferNotificationService
            StockTransferNotificationService.notify_transfer_cancelled(transfer)
            
            return Response({
                'success': True,
                'message': 'Transfer cancelled successfully'
            })
            
        except StockTransfer.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Transfer not found'
            }, status=status.HTTP_404_NOT_FOUND)


# Global Catalogue View for Business Admin
class GlobalCatalogueView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin'])]
    
    def get(self, request):
        tenant = request.user.tenant
        
        # Get all products with their inventory across all stores
        products = Product.objects.filter(tenant=tenant)
        
        catalogue_data = []
        for product in products:
            # Get inventory across all stores for this product
            inventory_data = []
            total_quantity = 0
            
            stores = tenant.stores.all()
            for store in stores:
                try:
                    inventory = ProductInventory.objects.get(product=product, store=store)
                    inventory_data.append({
                        'store_id': store.id,
                        'store_name': store.name,
                        'quantity': inventory.quantity,
                        'available_quantity': inventory.available_quantity,
                        'is_low_stock': inventory.is_low_stock,
                        'is_out_of_stock': inventory.is_out_of_stock
                    })
                    total_quantity += inventory.quantity
                except ProductInventory.DoesNotExist:
                    inventory_data.append({
                        'store_id': store.id,
                        'store_name': store.name,
                        'quantity': 0,
                        'available_quantity': 0,
                        'is_low_stock': False,
                        'is_out_of_stock': True
                    })
            
            catalogue_data.append({
                'product_id': product.id,
                'product_name': product.name,
                'product_sku': product.sku,
                'scope': product.scope,
                'store_name': product.store.name if product.store else 'Global',
                'total_quantity': total_quantity,
                'inventory_by_store': inventory_data
            })
        
        return Response({
            'catalogue': catalogue_data,
            'total_products': len(catalogue_data),
            'stores_count': tenant.stores.count()
        })


# Keep existing views for backward compatibility
class ProductVariantListView(generics.ListAPIView):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager', 'inhouse_sales', 'tele_calling', 'marketing'])]
    
    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        return ProductVariant.objects.filter(
            product_id=product_id,
            product__tenant=self.request.user.tenant
        )


class ProductVariantCreateView(generics.CreateAPIView):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def perform_create(self, serializer):
        product_id = self.kwargs.get('product_id')
        product = Product.objects.get(id=product_id, tenant=self.request.user.tenant)
        serializer.save(product=product)


class ProductVariantDetailView(generics.RetrieveAPIView):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager', 'inhouse_sales', 'tele_calling', 'marketing'])]
    
    def get_queryset(self):
        return ProductVariant.objects.filter(product__tenant=self.request.user.tenant)


class ProductVariantUpdateView(generics.UpdateAPIView):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def get_queryset(self):
        return ProductVariant.objects.filter(product__tenant=self.request.user.tenant)


class ProductVariantDeleteView(generics.DestroyAPIView):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager'])]
    
    def get_queryset(self):
        return ProductVariant.objects.filter(product__tenant=self.request.user.tenant)


class CategoryDebugView(APIView):
    """Debug view to check categories for current tenant"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        tenant = request.user.tenant
        categories = Category.objects.filter(tenant=tenant)
        return Response({
            'tenant': tenant.name,
            'categories_count': categories.count(),
            'categories': list(categories.values('id', 'name', 'is_active'))
        })


class ProductsDebugView(APIView):
    """Debug view to check products for current tenant"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        tenant = request.user.tenant
        products = Product.objects.filter(tenant=tenant)
        
        # Test the serializer
        serializer = ProductListSerializer(products, many=True)
        
        return Response({
            'tenant': tenant.name,
            'products_count': products.count(),
            'products': serializer.data,
            'gold_products': list(products.filter(category__name='Gold').values('id', 'name', 'category', 'category__name'))
        })


class ProductsByCategoryView(generics.ListAPIView):
    """Get products for a specific category"""
    serializer_class = ProductListSerializer
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager', 'inhouse_sales', 'tele_calling', 'marketing'])]
    pagination_class = None  # No pagination for category products
    
    def get_queryset(self):
        category_id = self.kwargs.get('category_id')
        user = self.request.user
        queryset = Product.objects.filter(
            tenant=user.tenant,
            category_id=category_id
        )
        
        # Apply scoped visibility
        if user.role != 'business_admin':
            queryset = queryset.filter(
                Q(store=user.store) | Q(scope='global')
            )
        
        return queryset.order_by('-created_at')


class PublicProductListView(generics.ListAPIView):
    """Public endpoint for viewing products by tenant/store slug"""
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomProductPagination
    
    def get_queryset(self):
        # Get tenant/store slug from URL parameter
        tenant_slug = self.kwargs.get('tenant_code')
        if not tenant_slug:
            return Product.objects.none()
        
        # Find tenant by slug
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            return Product.objects.none()
        
        queryset = Product.objects.filter(tenant=tenant, status='active')
        
        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Search by name or SKU
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(sku__icontains=search)
            )
        
        return queryset.order_by('-created_at')


class PublicCategoryListView(generics.ListAPIView):
    """Public endpoint for viewing categories by tenant/store slug"""
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    def get_queryset(self):
        # Get tenant/store slug from URL parameter
        tenant_slug = self.kwargs.get('tenant_code')
        if not tenant_slug:
            return Category.objects.none()
        
        # Find tenant by slug
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            return Category.objects.none()
        
        return Category.objects.filter(tenant=tenant, is_active=True)


class PublicProductDetailView(generics.RetrieveAPIView):
    """Public endpoint for viewing a specific product by tenant/store slug"""
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        # Get tenant/store slug from URL parameter
        tenant_slug = self.kwargs.get('tenant_code')
        if not tenant_slug:
            return Product.objects.none()
        
        # Find tenant by slug
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            return Product.objects.none()
        
        return Product.objects.filter(tenant=tenant, status='active')


class PublicProductsByCategoryView(generics.ListAPIView):
    """Public endpoint for viewing products by category and tenant/store slug"""
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    def get_queryset(self):
        # Get tenant/store slug and category ID from URL parameters
        tenant_slug = self.kwargs.get('tenant_code')
        category_id = self.kwargs.get('category_id')
        
        if not tenant_slug or not category_id:
            return Product.objects.none()
        
        # Find tenant by slug
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            return Product.objects.none()
        
        return Product.objects.filter(
            tenant=tenant,
            category_id=category_id,
            status='active'
        ).order_by('-created_at')


class ProductImportView(APIView):
    """
    Import products from CSV file.
    """
    permission_classes = [IsAuthenticated, IsRoleAllowed.for_roles(['business_admin', 'manager', 'inhouse_sales'])]
    parser_classes = [MultiPartParser, FormParser]  # Add this line to handle file uploads
    
    def get(self, request):
        """Test endpoint to check if import view is accessible"""
        return Response({
            'success': True,
            'message': 'Import endpoint is accessible'
        })
    
    def post(self, request):
        try:
            print(f"Import request from user: {request.user.username}, tenant: {request.user.tenant}")
            print(f"Request FILES: {request.FILES}")
            print(f"Request content type: {request.content_type}")
            
            if 'file' not in request.FILES:
                return Response({
                    'success': False,
                    'message': 'No file uploaded'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            file = request.FILES['file']
            print(f"File received: {file.name}, size: {file.size}, content_type: {file.content_type}")
            
            if not file.name.endswith('.csv'):
                return Response({
                    'success': False,
                    'message': 'Please upload a CSV file'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Read CSV file
            try:
                decoded_file = file.read().decode('utf-8')
                csv_data = csv.DictReader(io.StringIO(decoded_file))
                print(f"CSV file read successfully, headers: {csv_data.fieldnames}")
            except Exception as e:
                print(f"Error reading CSV file: {str(e)}")
                return Response({
                    'success': False,
                    'message': f'Error reading CSV file: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(csv_data, start=2):  # Start from 2 because row 1 is header
                try:
                    # Validate required fields
                    required_fields = ['name', 'sku', 'category', 'selling_price', 'cost_price']
                    missing_fields = []
                    for field in required_fields:
                        if not row.get(field):
                            missing_fields.append(field)
                    
                    if missing_fields:
                        errors.append(f"Row {row_num}: Missing required fields: {', '.join(missing_fields)}")
                        continue
                    
                    # Validate numeric fields
                    try:
                        selling_price = Decimal(row['selling_price'])
                        cost_price = Decimal(row['cost_price'])
                        quantity_str = row.get('quantity', '0')
                        quantity = int(quantity_str) if quantity_str.strip() else 0  # Default to 0 if empty or not provided
                    except (ValueError, TypeError) as e:
                        errors.append(f"Row {row_num}: Invalid numeric values - {str(e)}")
                        continue
                    
                    # Get or create category
                    category_name = row['category'].strip()
                    try:
                        # Set store and scope for category based on user role
                        store = None
                        scope = 'global'
                        
                        if request.user.role == 'manager':
                            store = request.user.store
                            scope = 'store'
                        elif request.user.role == 'business_admin':
                            # Business admin can create global categories
                            scope = 'global'
                        else:
                            # Other roles create store-specific categories
                            store = request.user.store
                            scope = 'store'
                        
                        category, created = Category.objects.get_or_create(
                            name=category_name,
                            tenant=request.user.tenant,
                            store=store,
                            scope=scope,
                            defaults={
                                'description': f'Category for {category_name}',
                                'is_active': True,
                                'store': store,
                                'scope': scope
                            }
                        )
                        if created:
                            print(f"Created new category: {category.name}")
                        else:
                            print(f"Using existing category: {category.name}")
                    except Exception as e:
                        print(f"Error creating/getting category: {str(e)}")
                        errors.append(f"Row {row_num}: Error with category '{category_name}' - {str(e)}")
                        continue
                    
                    # Check if SKU already exists (unique per tenant)
                    if Product.objects.filter(sku=row['sku'], tenant=request.user.tenant).exists():
                        errors.append(f"Row {row_num}: SKU '{row['sku']}' already exists in your tenant")
                        continue
                    
                    # Create product
                    try:
                        # Set store and scope based on user role
                        store = None
                        scope = 'global'
                        
                        if request.user.role == 'manager':
                            store = request.user.store
                            scope = 'store'
                        elif request.user.role == 'business_admin':
                            # Business admin can create global products
                            scope = 'global'
                        else:
                            # Other roles create store-specific products
                            store = request.user.store
                            scope = 'store'
                        
                        product = Product.objects.create(
                            name=row['name'].strip(),
                            sku=row['sku'].strip(),
                            category=category,
                            selling_price=selling_price,
                            cost_price=cost_price,
                            quantity=quantity,
                            description=row.get('description', '').strip(),
                            status='active',
                            tenant=request.user.tenant,
                            store=store,
                            scope=scope,
                            is_featured=False,
                            is_bestseller=False,
                            min_quantity=0,
                            max_quantity=999999,
                            weight=Decimal('0'),
                            dimensions='',
                            material='',
                            color='',
                            size='',
                            brand='',
                            main_image='',
                            additional_images=[],
                            meta_title='',
                            meta_description='',
                            tags=[]
                        )
                    except Exception as e:
                        print(f"Error creating product: {str(e)}")
                        errors.append(f"Row {row_num}: Error creating product - {str(e)}")
                        continue
                    
                    print(f"Successfully created product: {product.name} (SKU: {product.sku})")
                    imported_count += 1
                    
                except Exception as e:
                    print(f"Error processing row {row_num}: {str(e)}")
                    errors.append(f"Row {row_num}: {str(e)}")
                    continue
            
            if errors:
                return Response({
                    'success': False,
                    'message': f'Import completed with {len(errors)} errors',
                    'imported_count': imported_count,
                    'errors': errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': True,
                'message': f'Successfully imported {imported_count} products',
                'imported_count': imported_count
            })
            
        except Exception as e:
            print(f"Import failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'message': f'Import failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
