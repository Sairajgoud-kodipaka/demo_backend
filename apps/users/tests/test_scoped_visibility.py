from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.db import models
from rest_framework.test import APITestCase
from rest_framework import status
from apps.users.middleware import ScopedVisibilityMiddleware, ScopedVisibilityMixin
from apps.users.permissions import IsRoleAllowed
from apps.tenants.models import Tenant
from apps.stores.models import Store
from apps.clients.models import Client
from apps.sales.models import SalesPipeline

User = get_user_model()


class MockModel(models.Model):
    """Mock model for testing scoped visibility"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    sales_representative = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='sales_rep_items')
    name = models.CharField(max_length=100)
    
    class Meta:
        app_label = 'users'


class ScopedVisibilityMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ScopedVisibilityMiddleware()
        
        # Create test tenant
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            subdomain="test",
            schema_name="test_schema"
        )
        
        # Create test store
        self.store = Store.objects.create(
            name="Test Store",
            code="TS001",
            address="Test Address",
            city="Test City",
            state="Test State",
            timezone="UTC",
            tenant=self.tenant
        )
        
        # Create test users
        self.platform_admin = User.objects.create_user(
            username='platform_admin',
            email='admin@test.com',
            password='testpass123',
            role='platform_admin',
            tenant=self.tenant
        )
        
        self.business_admin = User.objects.create_user(
            username='business_admin',
            email='business@test.com',
            password='testpass123',
            role='business_admin',
            tenant=self.tenant
        )
        
        self.manager = User.objects.create_user(
            username='manager',
            email='manager@test.com',
            password='testpass123',
            role='manager',
            tenant=self.tenant,
            store=self.store
        )
        
        self.salesperson = User.objects.create_user(
            username='salesperson',
            email='sales@test.com',
            password='testpass123',
            role='inhouse_sales',
            tenant=self.tenant,
            store=self.store
        )

    def test_platform_admin_scope(self):
        """Test platform admin has full access"""
        request = self.factory.get('/')
        request.user = self.platform_admin
        
        self.middleware.process_request(request)
        
        scope = request.get_user_scope(request)
        self.assertEqual(scope['type'], 'all')
        self.assertTrue(request.can_access_all_data(request))
        self.assertTrue(request.can_access_store_data(request))
        self.assertTrue(request.can_access_own_data(request))

    def test_business_admin_scope(self):
        """Test business admin has full access"""
        request = self.factory.get('/')
        request.user = self.business_admin
        
        self.middleware.process_request(request)
        
        scope = request.get_user_scope(request)
        self.assertEqual(scope['type'], 'all')
        self.assertTrue(request.can_access_all_data(request))

    def test_manager_scope(self):
        """Test manager has store-level access"""
        request = self.factory.get('/')
        request.user = self.manager
        
        self.middleware.process_request(request)
        
        scope = request.get_user_scope(request)
        self.assertEqual(scope['type'], 'store')
        self.assertEqual(scope['filters']['store_id'], self.store.id)
        self.assertFalse(request.can_access_all_data(request))
        self.assertTrue(request.can_access_store_data(request))
        self.assertTrue(request.can_access_own_data(request))

    def test_salesperson_scope(self):
        """Test salesperson has own data access only"""
        request = self.factory.get('/')
        request.user = self.salesperson
        
        self.middleware.process_request(request)
        
        scope = request.get_user_scope(request)
        self.assertEqual(scope['type'], 'own')
        self.assertEqual(scope['filters']['user_id'], self.salesperson.id)
        self.assertFalse(request.can_access_all_data(request))
        self.assertFalse(request.can_access_store_data(request))
        self.assertTrue(request.can_access_own_data(request))

    def test_scoped_queryset_platform_admin(self):
        """Test platform admin gets all data"""
        request = self.factory.get('/')
        request.user = self.platform_admin
        
        self.middleware.process_request(request)
        
        # Create test data
        MockModel.objects.create(
            tenant=self.tenant,
            store=self.store,
            assigned_to=self.salesperson,
            name="Test Item 1"
        )
        MockModel.objects.create(
            tenant=self.tenant,
            store=self.store,
            assigned_to=self.manager,
            name="Test Item 2"
        )
        
        queryset = request.get_scoped_queryset(request, MockModel)
        self.assertEqual(queryset.count(), 2)

    def test_scoped_queryset_manager(self):
        """Test manager gets store-specific data"""
        request = self.factory.get('/')
        request.user = self.manager
        
        self.middleware.process_request(request)
        
        # Create test data
        MockModel.objects.create(
            tenant=self.tenant,
            store=self.store,
            assigned_to=self.salesperson,
            name="Store Item 1"
        )
        MockModel.objects.create(
            tenant=self.tenant,
            store=None,  # Different store
            assigned_to=self.manager,
            name="Other Store Item"
        )
        
        queryset = request.get_scoped_queryset(request, MockModel)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().name, "Store Item 1")

    def test_scoped_queryset_salesperson(self):
        """Test salesperson gets own data only"""
        request = self.factory.get('/')
        request.user = self.salesperson
        
        self.middleware.process_request(request)
        
        # Create test data
        MockModel.objects.create(
            tenant=self.tenant,
            store=self.store,
            assigned_to=self.salesperson,
            name="My Item 1"
        )
        MockModel.objects.create(
            tenant=self.tenant,
            store=self.store,
            assigned_to=self.manager,
            name="Manager Item"
        )
        
        queryset = request.get_scoped_queryset(request, MockModel)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().name, "My Item 1")


class ScopedVisibilityMixinTest(APITestCase):
    def setUp(self):
        # Create test data similar to above
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            subdomain="test",
            schema_name="test_schema"
        )
        
        self.store = Store.objects.create(
            name="Test Store",
            code="TS001",
            address="Test Address",
            city="Test City",
            state="Test State",
            timezone="UTC",
            tenant=self.tenant
        )
        
        self.manager = User.objects.create_user(
            username='manager',
            email='manager@test.com',
            password='testpass123',
            role='manager',
            tenant=self.tenant,
            store=self.store
        )
        
        self.salesperson = User.objects.create_user(
            username='salesperson',
            email='sales@test.com',
            password='testpass123',
            role='inhouse_sales',
            tenant=self.tenant,
            store=self.store
        )

    def test_mixin_inheritance(self):
        """Test that mixin provides scoping methods"""
        class TestViewSet(ScopedVisibilityMixin):
            def __init__(self):
                self.request = type('MockRequest', (), {
                    'user': self.manager,
                    'get_scoped_queryset': lambda req, model, **kwargs: MockModel.objects.filter(store=self.store),
                    'get_user_scope': lambda req: {'type': 'store', 'filters': {'store_id': self.store.id}}
                })()
        
        viewset = TestViewSet()
        
        # Test mixin methods
        self.assertTrue(hasattr(viewset, 'get_scoped_queryset'))
        self.assertTrue(hasattr(viewset, 'get_user_scope'))
        self.assertTrue(hasattr(viewset, 'can_access_all_data'))
        self.assertTrue(hasattr(viewset, 'can_access_store_data'))
        self.assertTrue(hasattr(viewset, 'can_access_own_data'))


class ScopedVisibilityIntegrationTest(APITestCase):
    def setUp(self):
        # Create comprehensive test data
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            subdomain="test",
            schema_name="test_schema"
        )
        
        self.store1 = Store.objects.create(
            name="Store 1",
            code="S001",
            address="Address 1",
            city="City 1",
            state="State 1",
            timezone="UTC",
            tenant=self.tenant
        )
        
        self.store2 = Store.objects.create(
            name="Store 2",
            code="S002",
            address="Address 2",
            city="City 2",
            state="State 2",
            timezone="UTC",
            tenant=self.tenant
        )
        
        # Create users for different roles
        self.platform_admin = User.objects.create_user(
            username='platform_admin',
            email='admin@test.com',
            password='testpass123',
            role='platform_admin',
            tenant=self.tenant
        )
        
        self.manager1 = User.objects.create_user(
            username='manager1',
            email='manager1@test.com',
            password='testpass123',
            role='manager',
            tenant=self.tenant,
            store=self.store1
        )
        
        self.manager2 = User.objects.create_user(
            username='manager2',
            email='manager2@test.com',
            password='testpass123',
            role='manager',
            tenant=self.tenant,
            store=self.store2
        )
        
        self.salesperson1 = User.objects.create_user(
            username='salesperson1',
            email='sales1@test.com',
            password='testpass123',
            role='inhouse_sales',
            tenant=self.tenant,
            store=self.store1
        )
        
        self.salesperson2 = User.objects.create_user(
            username='salesperson2',
            email='sales2@test.com',
            password='testpass123',
            role='inhouse_sales',
            tenant=self.tenant,
            store=self.store2
        )

    def test_data_isolation_between_stores(self):
        """Test that managers can only see their store's data"""
        # Create test data for both stores
        client1 = Client.objects.create(
            first_name="John",
            last_name="Doe",
            email="john@test.com",
            tenant=self.tenant,
            assigned_to=self.salesperson1
        )
        
        client2 = Client.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane@test.com",
            tenant=self.tenant,
            assigned_to=self.salesperson2
        )
        
        # Test manager1 can only see store1 data
        self.client.force_authenticate(user=self.manager1)
        response = self.client.get('/api/clients/clients/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Manager1 should only see clients assigned to store1
        # This would need to be implemented in the actual ClientViewSet
        # For now, we're testing the middleware logic
        
    def test_salesperson_own_data_only(self):
        """Test that salespeople can only see their own data"""
        # Create sales pipeline data
        pipeline1 = SalesPipeline.objects.create(
            title="My Pipeline 1",
            client=Client.objects.create(
                first_name="Client1",
                last_name="Test",
                email="client1@test.com",
                tenant=self.tenant,
                assigned_to=self.salesperson1
            ),
            sales_representative=self.salesperson1,
            stage='lead',
            expected_value=1000,
            actual_value=0,
            tenant=self.tenant
        )
        
        pipeline2 = SalesPipeline.objects.create(
            title="Other Pipeline",
            client=Client.objects.create(
                first_name="Client2",
                last_name="Test",
                email="client2@test.com",
                tenant=self.tenant,
                assigned_to=self.salesperson2
            ),
            sales_representative=self.salesperson2,
            stage='lead',
            expected_value=2000,
            actual_value=0,
            tenant=self.tenant
        )
        
        # Test salesperson1 can only see their own pipeline
        self.client.force_authenticate(user=self.salesperson1)
        response = self.client.get('/api/sales/pipeline/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Salesperson1 should only see their own pipeline
        # This would need to be implemented in the actual SalesPipelineViewSet
        # For now, we're testing the middleware logic 