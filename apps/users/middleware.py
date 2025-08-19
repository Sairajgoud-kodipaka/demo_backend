from django.db.models import Q
from django.utils.deprecation import MiddlewareMixin
from rest_framework.request import Request


class ScopedVisibilityMiddleware(MiddlewareMixin):
    """
    Middleware to handle scoped visibility based on user roles.
    This middleware adds scoping methods to the request object.
    """
    
    def process_request(self, request):
        """Add scoping methods to the request object."""
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Store the middleware instance on the request for access in views
            request._scoped_visibility_middleware = self
        else:
            # Still attach middleware for unauthenticated requests
            request._scoped_visibility_middleware = self
    
    def get_user_scope(self, request):
        """
        Get the scope configuration for the current user.
        Returns a dict with scope type and filters.
        """
        user = request.user
        
        if user.role in ['platform_admin', 'business_admin']:
            return {
                'type': 'all',
                'filters': {},
                'description': 'Full access to all data'
            }
        elif user.role == 'manager':
            return {
                'type': 'store',
                'filters': {'store_id': user.store.id if user.store else None},
                'description': 'Access to store-specific data only'
            }
        elif user.role in ['inhouse_sales', 'tele_calling']:
            return {
                'type': 'own',
                'filters': {'user_id': user.id},
                'description': 'Access to own data only'
            }
        else:
            return {
                'type': 'none',
                'filters': {},
                'description': 'No access'
            }
    
    def can_access_all_data(self, request):
        """Check if user can access all data (no restrictions)."""
        user = request.user
        return user.role in ['platform_admin', 'business_admin']
    
    def can_access_store_data(self, request):
        """Check if user can access store-specific data."""
        user = request.user
        return user.role in ['manager', 'platform_admin', 'business_admin']
    
    def can_access_own_data(self, request):
        """Check if user can access their own data."""
        user = request.user
        return user.role in ['inhouse_sales', 'tele_calling', 'manager', 'platform_admin', 'business_admin']
    
    def get_scoped_queryset(self, request, model_class, **additional_filters):
        """
        Get a scoped queryset based on user role and store affiliation.
        
        Args:
            request: The request object
            model_class: The Django model class
            **additional_filters: Additional filters to apply
            
        Returns:
            Filtered queryset based on user scope
        """
        user = request.user
        
        queryset = model_class.objects.all()
        
        # Apply tenant filtering first
        if hasattr(model_class, 'tenant') and user.tenant:
            queryset = queryset.filter(tenant=user.tenant)
        
        # Apply role-based scoping
        if user.role in ['platform_admin', 'business_admin']:
            # No additional filtering - full access
            pass
        elif user.role == 'manager':
            # Store Manager: Filter by store_id - comprehensive store-based filtering
            if user.store:
                # Direct store filtering for models with store field
                if hasattr(model_class, 'store'):
                    queryset = queryset.filter(store=user.store)
                
                # For models that have assigned_to field, filter by users in the same store
                elif hasattr(model_class, 'assigned_to'):
                    queryset = queryset.filter(assigned_to__store=user.store)
                
                # For sales pipeline models
                elif hasattr(model_class, 'sales_representative'):
                    queryset = queryset.filter(sales_representative__store=user.store)
                
                # For models with created_by field, filter by users in the same store
                elif hasattr(model_class, 'created_by'):
                    queryset = queryset.filter(created_by__store=user.store)
                
                # For models with user field, filter by users in the same store
                elif hasattr(model_class, 'user'):
                    queryset = queryset.filter(user__store=user.store)
                
                # For client-related models (appointments, followups, tasks)
                elif hasattr(model_class, 'client'):
                    # Filter by clients from the same store
                    if hasattr(model_class.client.field.related_model, 'store'):
                        queryset = queryset.filter(client__store=user.store)
                    else:
                        # Fallback to client's assigned user's store
                        queryset = queryset.filter(client__assigned_to__store=user.store)
                
                # For sale-related models
                elif hasattr(model_class, 'client') and hasattr(model_class, 'sales_representative'):
                    # For sales, filter by both client store and sales rep store
                    queryset = queryset.filter(
                        client__store=user.store,
                        sales_representative__store=user.store
                    )
                
                # For models without direct store relationship, filter by tenant only
                else:
                    pass
            else:
                pass
        elif user.role in ['inhouse_sales', 'tele_calling']:
            # Salesperson: Filter by user_id (own data only)
            
            # Special case for Client-related models - sales people can see all clients/appointments/followups from their store
            if (model_class._meta.app_label == 'clients' and 
                user.store):
                if model_class._meta.model_name == 'client':
                    # For clients, use direct store relationship for better performance
                    if hasattr(model_class, 'store'):
                        queryset = queryset.filter(store=user.store)
                    else:
                        # Fallback to assigned_to store filtering
                        queryset = queryset.filter(assigned_to__store=user.store)
                elif model_class._meta.model_name in ['appointment', 'followup']:
                    # For appointments and followups, allow access to those related to clients from the same store
                    if hasattr(model_class, 'client') and hasattr(model_class.client.field.related_model, 'store'):
                        queryset = queryset.filter(client__store=user.store)
                    else:
                        # Fallback to assigned_to store filtering
                        queryset = queryset.filter(client__assigned_to__store=user.store)
                elif model_class._meta.model_name == 'task':
                    # For tasks, allow access to those related to clients from the same store
                    if hasattr(model_class, 'client') and hasattr(model_class.client.field.related_model, 'store'):
                        queryset = queryset.filter(client__store=user.store)
                    else:
                        # Fallback to assigned_to store filtering
                        queryset = queryset.filter(client__assigned_to__store=user.store)
            elif hasattr(model_class, 'assigned_to'):
                queryset = queryset.filter(assigned_to=user)
            elif hasattr(model_class, 'sales_representative'):
                queryset = queryset.filter(sales_representative=user)
            elif hasattr(model_class, 'created_by'):
                queryset = queryset.filter(created_by=user)
            elif hasattr(model_class, 'user'):
                queryset = queryset.filter(user=user)

        # Apply additional filters
        for field, value in additional_filters.items():
            if value is not None:
                queryset = queryset.filter(**{field: value})

        return queryset


class ScopedVisibilityMixin:
    """
    Mixin to add scoped visibility methods to ViewSets and APIViews.
    """

    def get_scoped_queryset(self, model_class=None, **additional_filters):
        """
        Get a scoped queryset for the current view.

        Args:
            model_class: The model class to filter (defaults to self.queryset.model)
            **additional_filters: Additional filters to apply

        Returns:
            Filtered queryset based on user scope
        """
        
        if model_class is None:
            model_class = self.queryset.model

        # Get the middleware instance from the request
        middleware = getattr(self.request, '_scoped_visibility_middleware', None)
        
        if middleware is None:
            return model_class.objects.all()

        return middleware.get_scoped_queryset(self.request, model_class, **additional_filters)

    def get_user_scope(self):
        """Get the current user's scope configuration."""
        middleware = getattr(self.request, '_scoped_visibility_middleware', None)
        if middleware is None:
            return {'type': 'none', 'filters': {}, 'description': 'No middleware available'}
        return middleware.get_user_scope(self.request)

    def can_access_all_data(self):
        """Check if current user can access all data."""
        middleware = getattr(self.request, '_scoped_visibility_middleware', None)
        if middleware is None:
            return False
        return middleware.can_access_all_data(self.request)

    def can_access_store_data(self):
        """Check if current user can access store-specific data."""
        middleware = getattr(self.request, '_scoped_visibility_middleware', None)
        if middleware is None:
            return False
        return middleware.can_access_store_data(self.request)

    def can_access_own_data(self):
        """Check if current user can access their own data."""
        middleware = getattr(self.request, '_scoped_visibility_middleware', None)
        if middleware is None:
            return False
        return middleware.can_access_own_data(self.request) 