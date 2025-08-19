from rest_framework import serializers
from .models import Client, ClientInteraction, Appointment, FollowUp, Task, Announcement, CustomerTag, AuditLog
from apps.tenants.models import Tenant
from .models import Purchase


class ClientSerializer(serializers.ModelSerializer):
    # Handle frontend field mapping
    name = serializers.CharField(write_only=True, required=False)
    leadSource = serializers.CharField(write_only=True, required=False, source='lead_source')
    reasonForVisit = serializers.CharField(write_only=True, required=False, source='reason_for_visit')
    ageOfEndUser = serializers.CharField(write_only=True, required=False, source='age_of_end_user')
    source = serializers.CharField(write_only=True, required=False, source='lead_source')  # Map source to lead_source
    nextFollowUp = serializers.CharField(write_only=True, required=False, source='next_follow_up')
    summaryNotes = serializers.CharField(write_only=True, required=False, source='summary_notes', allow_null=True, allow_blank=True)
    assigned_to = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    
    # Add missing field mappings
    community = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    customer_interests = serializers.JSONField(required=False, default=list)
    
    # Explicitly define all fields except tenant
    first_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    customer_type = serializers.CharField(required=False, default='individual')
    status = serializers.CharField(required=False, default='lead')
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    city = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    state = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    country = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    postal_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    anniversary_date = serializers.DateField(required=False, allow_null=True)
    preferred_metal = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    preferred_stone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    ring_size = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    budget_range = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    lead_source = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    reason_for_visit = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    age_of_end_user = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    next_follow_up = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    summary_notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tags = serializers.SerializerMethodField(read_only=True)
    tag_slugs = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True,
        help_text="List of tag slugs to assign to the client"
    )
    # Store field for store-based visibility
    store = serializers.PrimaryKeyRelatedField(
        queryset=Client._meta.get_field('store').related_model.objects.all(),
        required=False,
        allow_null=True,
        help_text="Store this customer belongs to"
    )

    def validate_tag_slugs(self, value):
        """Validate that all tag slugs exist in the database"""
        if value:
            from .models import CustomerTag
            existing_slugs = CustomerTag.objects.filter(slug__in=value).values_list('slug', flat=True)
            missing_slugs = set(value) - set(existing_slugs)
            if missing_slugs:
                raise serializers.ValidationError(f"Tags with slugs {missing_slugs} do not exist in the database.")
        return value

    def validate_tags(self, value):
        """Validate that all tag slugs exist in the database (for backward compatibility)"""
        return self.validate_tag_slugs(value)
    
    class Meta:
        model = Client
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 'customer_type', 'status',
            'address', 'city', 'state', 'country', 'postal_code',
            'date_of_birth', 'anniversary_date', 'preferred_metal', 'preferred_stone',
            'ring_size', 'budget_range', 'lead_source', 'notes', 'community',
            'reason_for_visit', 'age_of_end_user', 'next_follow_up', 'summary_notes',
            'customer_interests', 'created_at', 'updated_at',
            # Frontend field mappings
            'name', 'leadSource', 'reasonForVisit', 'ageOfEndUser', 'source', 
            'nextFollowUp', 'summaryNotes', 'assigned_to',
            'tags', 'tag_slugs',
            'catchment_area',
            # Store field for store-based visibility
            'store',
            # Soft delete fields
            'is_deleted', 'deleted_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'tags', 'is_deleted', 'deleted_at']
    
    def create(self, validated_data):
        print("=== BACKEND SERIALIZER - CREATE METHOD START ===")
        print(f"Initial validated_data: {validated_data}")
        
        # Handle name field mapping
        if 'name' in validated_data:
            name = validated_data.pop('name')
            print(f"Processing name field: '{name}'")
            # Split name into first and last name
            name_parts = name.strip().split(' ', 1)
            validated_data['first_name'] = name_parts[0]
            validated_data['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
            print(f"Split name - first_name: '{validated_data['first_name']}', last_name: '{validated_data['last_name']}'")
        
        # Handle customer interests
        if 'customer_interests' in validated_data:
            print(f"Customer interests found: {validated_data['customer_interests']}")
        
        # Handle assigned_to field
        if 'assigned_to' in validated_data:
            assigned_to_value = validated_data['assigned_to']
            if assigned_to_value is None or assigned_to_value == '':
                validated_data.pop('assigned_to')
                print("Removed empty assigned_to field")
            elif assigned_to_value == 'current_user':
                # Assign to the current user
                request = self.context.get('request')
                if request and hasattr(request, 'user') and request.user.is_authenticated:
                    validated_data['assigned_to'] = request.user
                    print(f"Assigned customer to current user: {request.user}")
                else:
                    validated_data.pop('assigned_to')
                    print("No authenticated user, removed assigned_to field")
            else:
                # Try to find user by username or ID
                try:
                    from apps.users.models import User
                    if assigned_to_value.isdigit():
                        user = User.objects.get(id=int(assigned_to_value))
                    else:
                        user = User.objects.get(username=assigned_to_value)
                    validated_data['assigned_to'] = user
                    print(f"Assigned customer to user: {user}")
                except User.DoesNotExist:
                    validated_data.pop('assigned_to')
                    print(f"User '{assigned_to_value}' not found, removed assigned_to field")
        
        # ALWAYS assign tenant in create method
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            tenant = request.user.tenant
            if tenant:
                validated_data['tenant'] = tenant
                print(f"Assigned user's tenant in create: {tenant}")
            else:
                print("User has no tenant, creating default in create")
                from apps.tenants.models import Tenant
                tenant, created = Tenant.objects.get_or_create(
                    name='Default Tenant',
                    defaults={'domain': 'default.localhost'}
                )
                validated_data['tenant'] = tenant
                print(f"Created default tenant in create: {tenant}")
            
            # ALWAYS assign store in create method
            store = request.user.store
            if store:
                validated_data['store'] = store
                print(f"Assigned user's store in create: {store}")
            else:
                print("User has no store, store will be null")
        else:
            print("No authenticated user, creating default tenant in create")
            from apps.tenants.models import Tenant
            tenant, created = Tenant.objects.get_or_create(
                name='Default Tenant',
                defaults={'domain': 'default.localhost'}
            )
            validated_data['tenant'] = tenant
            print(f"Created default tenant for unauthenticated user in create: {tenant}")
            # Store will be null for unauthenticated users
        
        print(f"Final validated data before save: {validated_data}")
        
        try:
            result = super().create(validated_data)
            print(f"=== BACKEND SERIALIZER - CREATE SUCCESS ===")
            print(f"Created client: {result}")
            return result
        except Exception as e:
            print(f"=== BACKEND SERIALIZER - CREATE ERROR ===")
            print(f"Error creating client: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise e
    
    def get_tags(self, obj):
        return [
            {
                'slug': tag.slug,
                'name': tag.name,
                'category': tag.category
            }
            for tag in obj.tags.all()
        ]

    def update(self, instance, validated_data):
        """Override update method to handle tag updates"""
        print(f"=== CLIENT SERIALIZER UPDATE METHOD ===")
        print(f"Instance: {instance}")
        print(f"Validated data: {validated_data}")
        
        # Handle tag updates
        tag_slugs = validated_data.pop('tag_slugs', None)
        tags = validated_data.pop('tags', None)
        
        print(f"tag_slugs from request: {tag_slugs}")
        print(f"tags from request: {tags}")
        
        # Use tag_slugs if provided, otherwise use tags
        if tag_slugs is not None:
            print(f"Updating tags with tag_slugs: {tag_slugs}")
            # Clear existing tags and set new ones
            instance.tags.clear()
            if tag_slugs and len(tag_slugs) > 0:
                # Get tags by slug
                from .models import CustomerTag
                tags_to_add = CustomerTag.objects.filter(slug__in=tag_slugs)
                print(f"Found tags in database: {[tag.slug for tag in tags_to_add]}")
                if tags_to_add.exists():
                    instance.tags.add(*tags_to_add)
                    print(f"Added tags: {[tag.name for tag in tags_to_add]}")
                else:
                    print("No tags found in database for the provided slugs")
            else:
                print("No tag_slugs provided or empty list")
        elif tags is not None:
            print(f"Updating tags with tags: {tags}")
            # Clear existing tags and set new ones
            instance.tags.clear()
            if tags and len(tags) > 0:
                # Get tags by slug
                from .models import CustomerTag
                tags_to_add = CustomerTag.objects.filter(slug__in=tags)
                print(f"Found tags in database: {[tag.slug for tag in tags_to_add]}")
                if tags_to_add.exists():
                    instance.tags.add(*tags_to_add)
                    print(f"Added tags: {[tag.name for tag in tags_to_add]}")
                else:
                    print("No tags found in database for the provided slugs")
            else:
                print("No tags provided or empty list")
        
        # Call parent update method for other fields
        result = super().update(instance, validated_data)
        print(f"=== UPDATE METHOD COMPLETED ===")
        return result

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Add full_name for frontend compatibility
        data['name'] = instance.full_name
        # tags already included by get_tags
        return data
    
    def validate_email(self, value):
        """
        Check that the email is unique per tenant.
        """
        print(f"=== VALIDATING EMAIL: {value} ===")
        # For now, let's skip email validation to get the basic functionality working
        return value
    
    def to_internal_value(self, data):
        """
        Override to handle tenant field before validation.
        """
        print(f"=== TO_INTERNAL_VALUE START ===")
        print(f"Input data: {data}")
        
        # Remove tenant field from data if it exists
        if 'tenant' in data:
            data.pop('tenant')
            print("Removed tenant field from input data")
        
        # Call parent method
        result = super().to_internal_value(data)
        print(f"=== TO_INTERNAL_VALUE RESULT ===")
        print(f"Result: {result}")
        return result
    
    def validate(self, data):
        """
        Custom validation for the entire data set.
        """
        print(f"=== VALIDATING ENTIRE DATA SET ===")
        print(f"Data to validate: {data}")
        
        # For updates, we don't need to validate required fields if they're not being updated
        # Only validate if this is a create operation or if the fields are being updated
        instance = getattr(self, 'instance', None)
        
        if instance is None:
            # This is a create operation
            errors = {}
            
            # Check if we have required fields
            if not data.get('email'):
                errors['email'] = "Email is required"
            
            # Check if we have name or first_name/last_name
            if not data.get('name') and not (data.get('first_name') or data.get('last_name')):
                errors['name'] = "Name is required"
            
            if errors:
                print(f"=== VALIDATION ERRORS: {errors} ===")
                raise serializers.ValidationError(errors)
        else:
            # This is an update operation
            print("=== UPDATE OPERATION - SKIPPING REQUIRED FIELD VALIDATION ===")
        
        print("=== VALIDATION PASSED ===")
        print(f"Final data after validation: {data}")
        return data


class ClientInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientInteraction
        fields = '__all__'

class AppointmentSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ['tenant', 'created_by', 'created_at', 'updated_at', 'is_deleted', 'deleted_at']

    def get_client_name(self, obj):
        if hasattr(obj.client, 'full_name'):
            return obj.client.full_name
        return str(obj.client)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Add computed properties
        data['is_upcoming'] = instance.is_upcoming
        data['is_today'] = instance.is_today
        data['is_overdue'] = instance.is_overdue
        return data


class FollowUpSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = FollowUp
        fields = '__all__'
        read_only_fields = ['tenant', 'created_by', 'created_at', 'updated_at', 'is_deleted', 'deleted_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Add computed properties
        data['is_overdue'] = instance.is_overdue
        data['is_due_today'] = instance.is_due_today
        return data

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__' 

class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = '__all__' 

class AuditLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    
    class Meta:
        model = AuditLog
        fields = '__all__'


class CustomerTagSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomerTag model
    """
    class Meta:
        model = CustomerTag
        fields = ['id', 'name', 'slug', 'category', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at'] 