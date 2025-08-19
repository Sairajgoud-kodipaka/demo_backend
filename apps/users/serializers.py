from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, TeamMember, TeamMemberActivity, TeamMemberPerformance
from apps.stores.models import Store


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    """
    store_name = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()
    store = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role',
            'phone', 'address', 'profile_picture', 'tenant', 'is_active',
            'created_at', 'updated_at', 'last_login',
            'store', 'store_name', 'tenant_name',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login']

    def get_store_name(self, obj):
        return obj.store.name if obj.store else None

    def get_tenant_name(self, obj):
        return obj.tenant.name if obj.tenant else None


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users (Admin only).
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name', 
            'role', 'phone', 'address', 'store', 'tenant'
        ]
        read_only_fields = ['tenant']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MessagingUserSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for messaging users.
    Only includes essential fields needed for the frontend.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'phone', 'address'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile updates.
    """
    tenant = serializers.PrimaryKeyRelatedField(read_only=True)
    tenant_name = serializers.SerializerMethodField()
    store_name = serializers.SerializerMethodField()
    dashboard_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role',
            'phone', 'address', 'profile_picture', 'tenant', 'tenant_name',
            'store_name', 'dashboard_url'
        ]
        read_only_fields = ['id', 'username', 'tenant', 'role', 'dashboard_url']
    
    def get_tenant_name(self, obj):
        return obj.tenant.name if obj.tenant else None

    def get_store_name(self, obj):
        return obj.store.name if obj.store else None
    
    def get_dashboard_url(self, obj):
        """Return the appropriate dashboard URL based on user role."""
        role_dashboard_map = {
            'platform_admin': '/platform-admin/dashboard',
            'business_admin': '/business-admin/dashboard',
            'manager': '/managers/dashboard',
            'inhouse_sales': '/inhouse-sales/dashboard',
            'tele_calling': '/tele-calling/dashboard',
            'marketing': '/marketing/dashboard',
        }
        return role_dashboard_map.get(obj.role, '/dashboard')


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs


class TeamMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for TeamMember model.
    """
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    manager_name = serializers.CharField(source='manager.user.get_full_name', read_only=True)
    sales_percentage = serializers.ReadOnlyField()
    is_performing_well = serializers.ReadOnlyField()
    performance_color = serializers.ReadOnlyField()

    class Meta:
        model = TeamMember
        fields = [
            'id', 'user', 'user_id', 'employee_id', 'department', 'position',
            'hire_date', 'status', 'performance_rating', 'sales_target',
            'current_sales', 'manager', 'manager_name', 'skills', 'notes',
            'sales_percentage', 'is_performing_well', 'performance_color',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'employee_id', 'created_at', 'updated_at']

    def validate_user_id(self, value):
        """Validate that the user exists and is not already a team member."""
        try:
            user = User.objects.get(id=value)
            if hasattr(user, 'team_member'):
                raise serializers.ValidationError("User is already a team member")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")

    def create(self, validated_data):
        user_id = validated_data.pop('user_id')
        user = User.objects.get(id=user_id)
        team_member = TeamMember.objects.create(user=user, **validated_data)
        return team_member


class TeamMemberListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for team member lists.
    """
    # User fields that match frontend expectations
    id = serializers.IntegerField(read_only=True)  # Team member ID
    user_id = serializers.IntegerField(source='user.id', read_only=True)  # User ID
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    store = serializers.PrimaryKeyRelatedField(source='user.store', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    tenant = serializers.PrimaryKeyRelatedField(source='user.tenant', read_only=True)
    created_at = serializers.DateTimeField(source='user.date_joined', read_only=True)
    updated_at = serializers.DateTimeField(source='user.date_joined', read_only=True)
    
    # Team member fields
    sales_percentage = serializers.ReadOnlyField()
    performance_color = serializers.ReadOnlyField()

    class Meta:
        model = TeamMember
        fields = [
            'id', 'user_id', 'first_name', 'last_name', 'email', 'role', 'phone', 
            'store', 'is_active', 'username', 'name', 'tenant', 'created_at', 'updated_at',
            'employee_id', 'department', 'position', 'status', 'performance_rating',
            'sales_target', 'current_sales', 'sales_percentage',
            'performance_color', 'hire_date',
        ]

    def to_representation(self, instance):
        """Add debugging to see what data is being serialized."""
        data = super().to_representation(instance)
        print(f"Serializing team member: {instance.user.get_full_name()} - Data: {data}")
        return data


class TeamMemberCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating team members with user data.
    """
    # User fields
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    role = serializers.ChoiceField(choices=User.Role.choices)
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.none(), required=False, allow_null=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter stores by current user's tenant
        request = self.context.get('request')
        if request and request.user and request.user.tenant:
            self.fields['store'].queryset = Store.objects.filter(tenant=request.user.tenant)
    
    # Team member fields
    department = serializers.CharField(max_length=50, required=False, allow_blank=True)
    position = serializers.CharField(max_length=100, required=False, allow_blank=True)
    hire_date = serializers.DateField(required=False)
    sales_target = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0.00)
    manager_id = serializers.IntegerField(required=False, allow_null=True)
    skills = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    notes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TeamMember
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name', 'role',
            'phone', 'address', 'store', 'department', 'position', 'hire_date', 
            'sales_target', 'manager_id', 'skills', 'notes'
        ]

    def validate_username(self, value):
        """Check that username is unique."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def validate_email(self, value):
        """Check that email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_manager_id(self, value):
        """Validate manager exists and is a team member."""
        if value is not None:
            try:
                manager = TeamMember.objects.get(id=value)
                return value
            except TeamMember.DoesNotExist:
                raise serializers.ValidationError("Manager does not exist")
        return value

    def create(self, validated_data):
        # Extract user data from the request data
        request_data = self.context.get('request').data
        request = self.context.get('request')
        current_user = request.user if request else None
        
        # Automatically assign store from current manager's store
        store = None
        if current_user and current_user.store:
            store = current_user.store
            print(f"Auto-assigning store: {store.name} (ID: {store.id})")
        else:
            # Fallback: try to get store from request data
            store_id = request_data.get('store')
            if store_id:
                try:
                    store = Store.objects.get(id=store_id)
                    print(f"Using store from request: {store.name} (ID: {store.id})")
                except Store.DoesNotExist:
                    print(f"Store with ID {store_id} not found")
        
        user_data = {
            'username': request_data.get('username'),
            'email': request_data.get('email'),
            'first_name': request_data.get('first_name'),
            'last_name': request_data.get('last_name'),
            'role': request_data.get('role'),
            'phone': request_data.get('phone', ''),
            'address': request_data.get('address', ''),
            'is_active': True,  # Ensure user is active
            'store': store,
        }
        password = request_data.get('password')
        
        # Extract team member data - filter out user fields from validated_data
        team_member_fields = ['department', 'position', 'hire_date', 'sales_target', 'manager_id', 'skills', 'notes']
        team_member_data = {k: v for k, v in validated_data.items() if k in team_member_fields}
        
        # Extract manager_id separately
        manager_id = team_member_data.pop('manager_id', None)
        
        # Create user
        user = User(**user_data)
        user.set_password(password)
        
        # Set tenant based on store or current user
        if store:
            user.tenant = store.tenant
        elif current_user and current_user.tenant:
            user.tenant = current_user.tenant
        
        user.save()
        
        # Generate unique employee_id
        import random
        while True:
            employee_id = random.randint(1000, 9999)
            if not TeamMember.objects.filter(employee_id=employee_id).exists():
                break
        
        # Create team member with unique employee_id
        team_member = TeamMember.objects.create(
            user=user, 
            employee_id=employee_id,
            **team_member_data
        )
        
        # Set manager if provided, otherwise set current user as manager
        if manager_id:
            try:
                manager = TeamMember.objects.get(id=manager_id)
                team_member.manager = manager
            except TeamMember.DoesNotExist:
                pass
        elif current_user:
            # Set current user as manager if no manager specified
            try:
                current_manager = TeamMember.objects.get(user=current_user)
                team_member.manager = current_manager
            except TeamMember.DoesNotExist:
                pass
        
        team_member.save()
        
        print(f"Team member created successfully: {team_member.id}, Employee ID: {employee_id}")
        return team_member

    def to_representation(self, instance):
        """Return a flattened representation that matches frontend expectations."""
        return {
            'id': instance.id,
            'user_id': instance.user.id,
            'username': instance.user.username,
            'email': instance.user.email,
            'first_name': instance.user.first_name,
            'last_name': instance.user.last_name,
            'name': instance.user.get_full_name(),
            'role': instance.user.role,
            'phone': instance.user.phone,
            'address': instance.user.address,
            'store': instance.user.store.id if instance.user.store else None,
            'tenant': instance.user.tenant.id if instance.user.tenant else None,
            'is_active': instance.user.is_active,
            'created_at': instance.user.date_joined.isoformat(),
            'updated_at': instance.user.date_joined.isoformat(),
            'department': instance.department,
            'position': instance.position,
            'hire_date': instance.hire_date.isoformat() if instance.hire_date else None,
            'sales_target': str(instance.sales_target) if instance.sales_target else '0.00',
            'skills': instance.skills or [],
            'notes': instance.notes,
        }


class TeamMemberUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating team members.
    """
    # User fields that can be updated (without source to handle flat data)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all(), required=False, allow_null=True)
    
    # Team member fields
    department = serializers.CharField(required=False, allow_blank=True)
    position = serializers.CharField(required=False, allow_blank=True)
    hire_date = serializers.DateField(required=False)
    status = serializers.ChoiceField(choices=TeamMember.Status.choices, required=False)
    performance_rating = serializers.ChoiceField(choices=TeamMember.Performance.choices, required=False)
    sales_target = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    skills = serializers.ListField(child=serializers.CharField(), required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TeamMember
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 'role', 'store',
            'department', 'position', 'hire_date', 'status', 'performance_rating',
            'sales_target', 'skills', 'notes'
        ]
        read_only_fields = ['id']

    def validate_email(self, value):
        """Check that email is unique if changed."""
        if value and User.objects.filter(email=value).exclude(id=self.instance.user.id).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def update(self, instance, validated_data):
        # Update user fields
        user_data = {}
        for field in ['first_name', 'last_name', 'email', 'phone', 'role', 'store']:
            if field in validated_data:
                user_data[field] = validated_data.pop(field)
        
        if user_data:
            for field, value in user_data.items():
                setattr(instance.user, field, value)
            instance.user.save()
        
        # Update team member fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
        
        instance.save()
        return instance


class TeamMemberActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for team member activities.
    """
    team_member_name = serializers.CharField(source='team_member.user.get_full_name', read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)

    class Meta:
        model = TeamMemberActivity
        fields = [
            'id', 'team_member', 'team_member_name', 'activity_type',
            'activity_type_display', 'description', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TeamMemberPerformanceSerializer(serializers.ModelSerializer):
    """
    Serializer for team member performance records.
    """
    team_member_name = serializers.CharField(source='team_member.user.get_full_name', read_only=True)
    sales_percentage = serializers.ReadOnlyField()
    conversion_rate = serializers.ReadOnlyField()

    class Meta:
        model = TeamMemberPerformance
        fields = [
            'id', 'team_member', 'team_member_name', 'month', 'sales_target',
            'actual_sales', 'leads_generated', 'deals_closed',
            'customer_satisfaction', 'notes', 'sales_percentage',
            'conversion_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TeamStatsSerializer(serializers.Serializer):
    """
    Serializer for team statistics.
    """
    total_members = serializers.IntegerField()
    active_members = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_performance = serializers.DecimalField(max_digits=5, decimal_places=2)
    top_performers = serializers.ListField()
    recent_activities = serializers.ListField() 