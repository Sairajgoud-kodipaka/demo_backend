from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Tenant
from apps.clients.models import Client
from apps.sales.models import Sale, SalesPipeline
from apps.stores.models import Store
from decimal import Decimal

User = get_user_model()

class BusinessDashboardViewTest(APITestCase):
    def setUp(self):
        # Create a tenant
        self.tenant = Tenant.objects.create(
            name="Test Business",
            business_type="Jewelry",
            subscription_status="active"
        )
        
        # Create a store
        self.store = Store.objects.create(
            name="Main Store",
            code="MS001",
            address="123 Test St",
            city="Test City",
            state="Test State",
            timezone="Asia/Kolkata",
            tenant=self.tenant
        )
        
        # Create a business admin user
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role=User.Role.BUSINESS_ADMIN,
            tenant=self.tenant
        )
        
        # Create a manager user
        self.manager_user = User.objects.create_user(
            username="manager",
            email="manager@test.com",
            password="testpass123",
            role=User.Role.MANAGER,
            tenant=self.tenant,
            store=self.store
        )
        
        # Create an inhouse sales user
        self.sales_user = User.objects.create_user(
            username="sales",
            email="sales@test.com",
            password="testpass123",
            role=User.Role.INHOUSE_SALES,
            tenant=self.tenant,
            store=self.store
        )
        
        # Create a client
        self.client_obj = Client.objects.create(
            first_name="John",
            last_name="Doe",
            email="john@test.com",
            phone="1234567890",
            tenant=self.tenant,
            store=self.store
        )
        
        # Create a sale
        self.sale = Sale.objects.create(
            order_number="ORD001",
            client=self.client_obj,
            sales_representative=self.admin_user,
            status=Sale.Status.CONFIRMED,
            payment_status=Sale.PaymentStatus.PAID,
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("1100.00"),
            paid_amount=Decimal("1100.00"),
            tenant=self.tenant
        )
        
        # Create a sales pipeline
        self.pipeline = SalesPipeline.objects.create(
            title="Test Pipeline",
            client=self.client_obj,
            sales_representative=self.admin_user,
            stage=SalesPipeline.Stage.LEAD,
            probability=50,
            expected_value=Decimal("2000.00"),
            actual_value=Decimal("0.00"),
            tenant=self.tenant
        )

    def test_business_dashboard_returns_correct_structure(self):
        """Test that the business dashboard returns the expected data structure"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/tenants/dashboard/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        
        # Check that all required fields are present
        self.assertIn('total_sales', data)
        self.assertIn('pipeline_revenue', data)
        self.assertIn('closed_won_pipeline_count', data)
        self.assertIn('pipeline_deals_count', data)
        self.assertIn('store_performance', data)
        self.assertIn('top_managers', data)
        self.assertIn('top_salesmen', data)
        
        # Check total_sales structure
        total_sales = data['total_sales']
        self.assertIn('today', total_sales)
        self.assertIn('week', total_sales)
        self.assertIn('month', total_sales)
        
        # Check that values are numeric
        self.assertIsInstance(data['pipeline_revenue'], (int, float))
        self.assertIsInstance(data['closed_won_pipeline_count'], int)
        self.assertIsInstance(data['pipeline_deals_count'], int)
        
        # Check that store_performance is a list
        self.assertIsInstance(data['store_performance'], list)
        
        # Check that top_managers and top_salesmen are lists
        self.assertIsInstance(data['top_managers'], list)
        self.assertIsInstance(data['top_salesmen'], list)

    def test_business_dashboard_requires_authentication(self):
        """Test that the dashboard requires authentication"""
        response = self.client.get('/api/tenants/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_business_dashboard_allows_business_admin(self):
        """Test that business admin can access the dashboard"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/tenants/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_business_dashboard_allows_manager(self):
        """Test that manager can access the dashboard"""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.get('/api/tenants/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_business_dashboard_allows_inhouse_sales(self):
        """Test that inhouse sales can access the dashboard"""
        self.client.force_authenticate(user=self.sales_user)
        response = self.client.get('/api/tenants/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_business_dashboard_denies_other_roles(self):
        """Test that other roles cannot access the dashboard"""
        # Create a user with a different role
        other_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="testpass123",
            role=User.Role.TELE_CALLING,
            tenant=self.tenant
        )
        
        self.client.force_authenticate(user=other_user)
        response = self.client.get('/api/tenants/dashboard/')
        
        # Should return 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
