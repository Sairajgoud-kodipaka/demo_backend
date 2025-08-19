from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Store, StoreUserMap
from .serializers import StoreSerializer, StoreUserMapSerializer
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend

# Create your views here.

class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Store.objects.all()
        if hasattr(user, 'is_platform_admin') and user.is_platform_admin:
            return queryset
        # All users (including business admins) only see their tenant's stores
        if user.tenant:
            return queryset.filter(tenant=user.tenant)
        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        print("DEBUG: Creating store for user", user, "tenant", user.tenant)
        if not user.tenant:
            raise ValidationError({"detail": "Your user account is not assigned to a tenant. Please contact your administrator."})
        # Only platform admin can set tenant explicitly
        if hasattr(user, 'is_platform_admin') and user.is_platform_admin:
            serializer.save()
        else:
            serializer.save(tenant=user.tenant)

    @action(detail=True, methods=['patch'], url_path='assign-team')
    def assign_team(self, request, pk=None):
        store = self.get_object()
        assignments = request.data.get('assignments', [])
        # Only allow users from the same tenant to be assigned
        for assignment in assignments:
            user_id = assignment.get('user')
            role = assignment.get('role')
            can_view_all = assignment.get('can_view_all', False)
            if not user_id or not role:
                continue
            # Check user belongs to the same tenant
            from apps.users.models import User
            try:
                user = User.objects.get(id=user_id, tenant=store.tenant)
            except User.DoesNotExist:
                continue
            StoreUserMap.objects.update_or_create(
                user=user, store=store, role=role,
                defaults={'can_view_all': can_view_all}
            )
        return Response({'status': 'team assigned'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='team')
    def get_team(self, request, pk=None):
        store = self.get_object()
        team = StoreUserMap.objects.filter(store=store)
        serializer = StoreUserMapSerializer(team, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='dashboard')
    def dashboard(self, request, pk=None):
        store = self.get_object()
        # Example KPIs: customer count, sales count, etc.
        from apps.clients.models import Client
        from apps.sales.models import Sale
        customer_count = Client.objects.filter(assigned_to__managed_stores=store).count()
        sales_count = Sale.objects.filter(sales_representative__managed_stores=store).count()
        # Add more KPIs as needed
        return Response({
            'customer_count': customer_count,
            'sales_count': sales_count,
        })

class StoreUserMapViewSet(viewsets.ModelViewSet):
    queryset = StoreUserMap.objects.all()
    serializer_class = StoreUserMapSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'store']
