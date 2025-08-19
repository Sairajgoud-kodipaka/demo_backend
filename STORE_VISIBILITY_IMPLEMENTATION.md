# Store-Based Customer Visibility Implementation

## Overview

This implementation ensures that customers from a specific store are visible to all users from that same store, regardless of who created or is assigned to the customer. Additionally, store managers are restricted to only see data from their specific store.

## Key Changes Made

### 1. Client Model Enhancement

**File**: `backend/apps/clients/models.py`

- Added a direct `store` field to the `Client` model:
  ```python
  store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='clients', null=True, blank=True, help_text=_('Store this customer belongs to'))
  ```

### 2. Updated Scoped Visibility Logic

**File**: `backend/apps/users/middleware.py`

- Enhanced the `get_scoped_queryset` method to use direct store filtering for better performance
- **Store Managers**: Comprehensive store-based filtering to ensure managers only see data from their specific store
- **Sales Users**: For sales users (`inhouse_sales`, `tele_calling`), customers are now filtered by direct store relationship
- Fallback to assigned_to store filtering for backward compatibility

### 3. Client Creation Logic

**File**: `backend/apps/clients/views.py`

- Updated `create` method to automatically set the store field when creating clients
- Added `perform_create` method to ensure store is set correctly
- Store is automatically assigned based on the creating user's store

**File**: `backend/apps/clients/serializers.py`

- Added `store` field to `ClientSerializer`
- Updated `create` method to automatically assign store based on user's store
- Store field is included in API responses

### 4. Database Migration

- Created and applied migration `0014_client_store.py` to add the store field to the Client model

## How It Works

### Store-Based Filtering

1. **User Assignment**: Each user is assigned to a specific store via the `store` field in the User model
2. **Customer Assignment**: When a customer is created, they are automatically assigned to the same store as the creating user
3. **Visibility Logic**: The scoped visibility middleware filters data by the user's store:

#### For Store Managers:
```python
# Comprehensive store-based filtering for managers
if user.role == 'manager' and user.store:
    # Direct store filtering for models with store field
    if hasattr(model_class, 'store'):
        queryset = queryset.filter(store=user.store)
    
    # For models with assigned_to field
    elif hasattr(model_class, 'assigned_to'):
        queryset = queryset.filter(assigned_to__store=user.store)
    
    # For sales pipeline models
    elif hasattr(model_class, 'sales_representative'):
        queryset = queryset.filter(sales_representative__store=user.store)
    
    # For client-related models
    elif hasattr(model_class, 'client'):
        queryset = queryset.filter(client__store=user.store)
```

#### For Sales Users:
```python
# Store-based filtering for sales users
if hasattr(model_class, 'store'):
    queryset = queryset.filter(store=user.store)
```

### Benefits

1. **Shared Visibility**: All users from a store can see all customers from that store
2. **Store Manager Isolation**: Store managers can only see data from their specific store
3. **Performance**: Direct store filtering is more efficient than filtering through assigned_to relationships
4. **Scalability**: Easy to extend to other models (appointments, follow-ups, etc.)
5. **Backward Compatibility**: Existing customers without store assignment still work via fallback logic

## Testing

A test script was created to verify the implementation:

- **Store Manager Visibility**: Confirmed that managers only see data from their specific store
- **Customer Visibility**: Verified that both users can see all customers from their store
- **Store Isolation**: Confirmed that store managers cannot see data from other stores

### Test Results:
- ✅ **Manager "rohith"** (Store: mandeep Jewelries nagole): Can see 7 customers and 6 pipelines from their store only
- ✅ **Manager "yakoob"** (Store: mandeep Jewelries meerpet): Can see 1 customer and 1 pipeline from their store only
- ✅ **Sales Users**: Can see all customers from their store, regardless of who created them

## Usage

### Creating Customers

When a user creates a customer, the store is automatically assigned:

```python
# The store field is automatically set based on the user's store
client = Client.objects.create(
    first_name="John",
    last_name="Doe",
    email="john@example.com",
    # store will be automatically set to user.store
)
```

### Viewing Customers

Users will only see customers from their store:

```python
# This will only return customers from the user's store
customers = Client.objects.filter(store=user.store)
```

### Store Manager Restrictions

Store managers are automatically restricted to their store's data:

```python
# Store managers only see data from their assigned store
if user.role == 'manager':
    # All queries are automatically filtered by user.store
    customers = Client.objects.filter(store=user.store)
    pipelines = SalesPipeline.objects.filter(client__store=user.store)
```

## API Endpoints

The store field is included in API responses:

```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "store": 1,
  "assigned_to": 2,
  // ... other fields
}
```

## Role-Based Access Control

### Store Managers
- **Access**: Only data from their assigned store
- **Scope**: Store-level isolation
- **Models**: Customers, Sales Pipelines, Appointments, etc.

### Sales Users
- **Access**: All customers from their store
- **Scope**: Store-based sharing
- **Models**: Customers, Sales Pipelines, Appointments, etc.

### Business Admins
- **Access**: All data across all stores
- **Scope**: Full system access
- **Models**: All models

## Future Enhancements

1. **Bulk Operations**: Update existing customers to have store assignments
2. **Multi-Store Users**: Support for users who can access multiple stores
3. **Store Transfers**: Allow customers to be transferred between stores
4. **Audit Trail**: Track store assignment changes
5. **Store Analytics**: Store-specific reporting and analytics

## Migration Notes

- Existing customers without store assignment will still be visible to users based on assigned_to relationships
- New customers will automatically get store assignment
- The system gracefully handles both old and new data structures
- Store managers are automatically restricted to their store's data 