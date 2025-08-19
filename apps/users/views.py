from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, TeamMember, TeamMemberActivity, TeamMemberPerformance
from .serializers import (
    UserSerializer, UserCreateSerializer, UserRegistrationSerializer, UserProfileSerializer,
    TeamMemberSerializer, TeamMemberListSerializer, TeamMemberCreateSerializer,
    TeamMemberUpdateSerializer, TeamMemberActivitySerializer, TeamMemberPerformanceSerializer, TeamStatsSerializer,
    MessagingUserSerializer
)
from apps.users.permissions import IsRoleAllowed
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import render
from django.db.models import Q
from .models import User
from .serializers import UserSerializer


class UserRegistrationView(generics.CreateAPIView):
    """
    Register a new user.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return User.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'User registered successfully',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveAPIView):
    """
    Get current user profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserProfileUpdateView(generics.UpdateAPIView):
    """
    Update current user profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    Change user password.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        # Validate input
        if not old_password or not new_password:
            return Response({
                'error': 'Both old_password and new_password are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if old password is correct
        if not user.check_password(old_password):
            return Response({
                'error': 'Current password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if new password is different from old password
        if old_password == new_password:
            return Response({
                'error': 'New password must be different from current password'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate new password strength
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({
                'error': e.messages[0] if e.messages else 'Password is not strong enough'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Change password
        user.set_password(new_password)
        user.save()

        # Log the password change for security audit
        print(f"Password changed for user: {user.username} ({user.role}) at {timezone.now()}")

        return Response({
            'message': 'Password changed successfully',
            'success': True
        }, status=status.HTTP_200_OK)


class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return User.objects.all()
        if user.is_business_admin or user.is_manager:
            return User.objects.filter(tenant=user.tenant)
        # Otherwise, only themselves
        return User.objects.filter(id=user.id)


class UserCreateView(generics.CreateAPIView):
    """
    Create a new user (Admin only).
    """
    serializer_class = UserCreateSerializer
    permission_classes = [IsRoleAllowed.for_roles(['platform_admin', 'business_admin', 'manager'])]

    def get_queryset(self):
        return User.objects.all()

    def create(self, request, *args, **kwargs):
        user = request.user

        # Only allow platform admin, business admin, or manager to create users
        allowed_roles = ['platform_admin', 'business_admin', 'manager']
        if user.role not in allowed_roles:
            return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

        # Managers can only create inhouse_sales, marketing, tele_calling for their own tenant
        if user.role == 'manager':
            role = request.data.get('role')
            if role not in ['inhouse_sales', 'marketing', 'tele_calling']:
                return Response({'detail': 'Managers can only add In-house Sales, Marketing, or Tele-calling users.'}, status=status.HTTP_403_FORBIDDEN)
            # Force the new user to have the same tenant as the manager
            request.data['tenant'] = user.tenant_id

        # Business admin can only create users for their own tenant
        if user.role == 'business_admin':
            request.data['tenant'] = user.tenant_id

        # Ensure user is active by default
        request.data['is_active'] = True

        response = super().create(request, *args, **kwargs)
        # Double-check and set is_active in case serializer ignores it
        if response.status_code == 201 and 'id' in response.data:
            try:
                created_user = User.objects.get(id=response.data['id'])
                if not created_user.is_active:
                    created_user.is_active = True
                    created_user.save()
            except Exception as e:
                print('Could not set user as active:', e)
        return response


class UserDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific user (Admin only).
    """
    serializer_class = UserSerializer
    permission_classes = [IsRoleAllowed.for_roles(['platform_admin'])]

    def get_queryset(self):
        return User.objects.all()


class UserUpdateView(generics.UpdateAPIView):
    """
    Update a specific user (Admin only).
    """
    serializer_class = UserSerializer
    permission_classes = [IsRoleAllowed.for_roles(['platform_admin'])]

    def get_queryset(self):
        return User.objects.all()


class UserDeleteView(generics.DestroyAPIView):
    """
    Delete a specific user (Admin only).
    """
    serializer_class = UserSerializer
    permission_classes = [IsRoleAllowed.for_roles(['platform_admin'])]

    def get_queryset(self):
        return User.objects.all()


# Team Member Views
class TeamMemberListView(generics.ListCreateAPIView):
    """
    List and create team members.
    """
    serializer_class = TeamMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Use different serializers for different operations."""
        if self.request.method == 'GET':
            return TeamMemberListSerializer
        elif self.request.method in ['PUT', 'PATCH']:
            return TeamMemberUpdateSerializer
        elif self.request.method == 'POST':
            return TeamMemberCreateSerializer
        return TeamMemberSerializer

    def create(self, request, *args, **kwargs):
        """Override create method to add debugging and better error handling."""
        try:
            print(f"TeamMemberListView.create called with data: {request.data}")
            return super().create(request, *args, **kwargs)
        except Exception as e:
            print(f"Error in TeamMemberListView.create: {e}")
            import traceback
            traceback.print_exc()
            raise

    def get_queryset(self):
        """Filter team members based on user's role, tenant, and store."""
        user = self.request.user
        queryset = TeamMember.objects.all()

        print(f"TeamMemberListView.get_queryset - User: {user.username}, Role: {user.role}, Tenant: {user.tenant}, Store: {user.store}")
        print(f"Request headers: {dict(self.request.headers)}")

        if user.is_platform_admin:
            print("User is platform admin - showing all team members")
            pass
        elif user.is_business_admin and user.tenant:
            print(f"User is business admin - filtering by tenant: {user.tenant}")
            queryset = queryset.filter(user__tenant=user.tenant)
        elif user.is_manager and user.tenant and user.store:
            # Managers can see all team members in their store
            print(f"User is manager - filtering by tenant: {user.tenant} and store: {user.store}")
            queryset = queryset.filter(user__tenant=user.tenant, user__store=user.store)
        elif user.is_manager and user.tenant:
            # Managers without specific store can see all team members in their tenant
            print(f"User is manager without store - filtering by tenant: {user.tenant}")
            queryset = queryset.filter(user__tenant=user.tenant)
        elif user.role == 'tele_caller' and user.tenant and user.store:
            print(f"User is tele_caller - filtering by tenant: {user.tenant} and store: {user.store}")
            queryset = queryset.filter(user__tenant=user.tenant, user__store=user.store, user__role='tele_caller')
        else:
            print(f"User is other role - showing only self")
            queryset = queryset.filter(user=user)

        store_id = self.request.query_params.get('store')
        if store_id:
            print(f"Additional store filter: {store_id}")
            queryset = queryset.filter(user__store_id=store_id)

        print(f"Final queryset count: {queryset.count()}")
        
        # Print the actual team members being returned
        for tm in queryset[:5]:  # Show first 5 for debugging
            print(f"  - {tm.user.get_full_name()} ({tm.user.username}) - Role: {tm.user.role}")
        
        return queryset


    def perform_create(self, serializer):
        """Set tenant for new team members."""
        user = self.request.user
        print(f"TeamMemberListView.perform_create for user: {user.username}, role: {user.role}")

        # Restrict manager to only create certain roles
        if user.role == 'manager':
            role = self.request.data.get('role')
            if role not in ['inhouse_sales', 'marketing', 'tele_calling']:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Managers can only add In-house Sales, Marketing, or Tele-calling users.")

            # Set manager field to self if not provided
            if not self.request.data.get('manager'):
                try:
                    manager_tm = TeamMember.objects.get(user=user)
                    serializer.validated_data['manager'] = manager_tm
                except TeamMember.DoesNotExist:
                    pass

        team_member = serializer.save()
        print(f"Team member created successfully: {team_member.id}")
        
        # Update manager if provided
        manager_id = self.request.data.get('manager')
        if manager_id:
            try:
                manager = TeamMember.objects.get(id=manager_id, user__tenant=user.tenant)
                team_member.manager = manager
                team_member.save()
            except TeamMember.DoesNotExist:
                print(f"Manager with ID {manager_id} not found")
                pass
        
        # Log activity
        TeamMemberActivity.objects.create(
            team_member=team_member,
            activity_type='task_completed',
            description=f'Team member {team_member.user.get_full_name()} was added to the team'
        )


class TeamMemberCreateView(generics.CreateAPIView):
    """
    Create a new team member.
    """
    serializer_class = TeamMemberCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Override create method to add debugging and better error handling."""
        try:
            print(f"Creating team member with data: {request.data}")
            return super().create(request, *args, **kwargs)
        except Exception as e:
            print(f"Error creating team member: {e}")
            import traceback
            traceback.print_exc()
            raise

    def perform_create(self, serializer):
        user = self.request.user
        print(f"Performing create for user: {user.username}, role: {user.role}")

        # Restrict manager to only create certain roles
        if user.role == 'manager':
            role = self.request.data.get('role')
            if role not in ['inhouse_sales', 'marketing', 'tele_calling']:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Managers can only add In-house Sales, Marketing, or Tele-calling users.")

            # Set manager field to self if not provided
            if not self.request.data.get('manager'):
                try:
                    manager_tm = TeamMember.objects.get(user=user)
                    serializer.validated_data['manager'] = manager_tm
                except TeamMember.DoesNotExist:
                    pass

        team_member = serializer.save()
        print(f"Team member created successfully: {team_member.id}")
        
        # Update manager if provided
        manager_id = self.request.data.get('manager')
        if manager_id:
            try:
                manager = TeamMember.objects.get(id=manager_id, user__tenant=user.tenant)
                team_member.manager = manager
                team_member.save()
            except TeamMember.DoesNotExist:
                print(f"Manager with ID {manager_id} not found")
                pass


class TeamMemberUpdateView(generics.UpdateAPIView):
    """
    Update a team member.
    """
    serializer_class = TeamMemberUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter team members based on user's role and tenant."""
        user = self.request.user
        
        # Get the user ID from the URL parameter
        user_id = self.kwargs.get('pk')
        
        if user.is_platform_admin:
            # Platform admin can update any team member
            if user_id:
                return TeamMember.objects.filter(user_id=user_id)
            return TeamMember.objects.all()
        
        if user.is_business_admin and user.tenant:
            # Business admin can update team members in their tenant
            if user_id:
                return TeamMember.objects.filter(user_id=user_id, user__tenant=user.tenant)
            return TeamMember.objects.filter(user__tenant=user.tenant)
        
        if user.is_manager:
            # Manager can update team members they manage or in their store
            if user_id:
                return TeamMember.objects.filter(
                    user_id=user_id
                ).filter(
                    Q(user=user) | Q(manager__user=user) | Q(user__store=user.store)
                )
            return TeamMember.objects.filter(
                Q(user=user) | Q(manager__user=user) | Q(user__store=user.store)
            )
        
        # Other users can only update themselves
        if user_id:
            return TeamMember.objects.filter(user_id=user_id, user=user)
        return TeamMember.objects.filter(user=user)

    def perform_update(self, serializer):
        """Log activity when team member is updated."""
        user = self.request.user
        team_member = serializer.save()
        
        # Prevent business admin from changing role of other business admins
        if user.is_business_admin and team_member.user.role == 'business_admin' and user.id != team_member.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Business admins cannot modify other business admins.")
        
        TeamMemberActivity.objects.create(
            team_member=team_member,
            activity_type='task_completed',
            description=f'Team member {team_member.user.get_full_name()} profile was updated'
        )
    
    def update(self, request, *args, **kwargs):
        """Override update method to return proper response."""
        try:
            print(f"Update request data: {request.data}")
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            print(f"Updating team member: {instance.id}, user: {instance.user.id}")
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            print(f"Update successful for team member: {instance.id}")
            
            return Response({
                'success': True,
                'message': 'Team member updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Update error: {e}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class TeamMemberDeleteView(generics.DestroyAPIView):
    """
    Delete a team member.
    """
    serializer_class = TeamMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter team members based on user's role and tenant."""
        user = self.request.user
        
        # Get the user ID from the URL parameter
        user_id = self.kwargs.get('pk')
        
        if user.is_platform_admin:
            # Platform admin can delete any team member
            if user_id:
                return TeamMember.objects.filter(user_id=user_id)
            return TeamMember.objects.all()
        
        if user.is_business_admin and user.tenant:
            # Business admin can delete team members in their tenant
            if user_id:
                return TeamMember.objects.filter(user_id=user_id, user__tenant=user.tenant)
            return TeamMember.objects.filter(user__tenant=user.tenant)
        
        if user.is_manager:
            # Manager can delete team members they manage or in their store
            if user_id:
                return TeamMember.objects.filter(
                    user_id=user_id
                ).filter(
                    Q(user=user) | Q(manager__user=user) | Q(user__store=user.store)
                )
            return TeamMember.objects.filter(
                Q(user=user) | Q(manager__user=user) | Q(user__store=user.store)
            )
        
        # Other users can only delete themselves
        if user_id:
            return TeamMember.objects.filter(user_id=user_id, user=user)
        return TeamMember.objects.filter(user=user)

    def perform_destroy(self, instance):
        """Log activity when team member is removed."""
        user = self.request.user
        user_name = instance.user.get_full_name()
        user_id = instance.user.id
        
        # Prevent business admin from deleting themselves
        if user.id == instance.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot delete your own account.")
        
        # Prevent business admin from deleting other business admins
        if user.is_business_admin and instance.user.role == 'business_admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Business admins cannot delete other business admins.")
        
        # Delete the team member (this will cascade to delete the user)
        instance.delete()
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy method to return proper response."""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'Team member deleted successfully'
        }, status=status.HTTP_200_OK)


class TeamMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete team members.
    """
    serializer_class = TeamMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method in ['PUT', 'PATCH']:
            return TeamMemberUpdateSerializer
        return TeamMemberSerializer

    def get_queryset(self):
        """Filter team members based on user's role and tenant."""
        user = self.request.user
        
        if user.is_platform_admin:
            return TeamMember.objects.all()
        
        if user.is_business_admin and user.tenant:
            return TeamMember.objects.filter(user__tenant=user.tenant)
        
        if user.is_manager:
            return TeamMember.objects.filter(
                Q(user=user) | Q(manager__user=user)
            )
        
        return TeamMember.objects.filter(user=user)

    def perform_update(self, serializer):
        """Log activity when team member is updated."""
        team_member = serializer.save()
        
        TeamMemberActivity.objects.create(
            team_member=team_member,
            activity_type='task_completed',
            description=f'Team member {team_member.user.get_full_name()} profile was updated'
        )
    
    def update(self, request, *args, **kwargs):
        """Override update method to add debugging."""
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            print(f"Update error: {e}")
            raise

    def perform_destroy(self, instance):
        """Log activity when team member is removed."""
        user_name = instance.user.get_full_name()
        user_id = instance.user.id
        
        # Delete the team member (this will cascade to delete the user)
        instance.delete()
        
        # Note: We can't log activity after deletion since the team_member is gone
        # The activity logging is handled by the cascade delete in the model


class TeamMemberActivityView(generics.ListCreateAPIView):
    """
    List and create team member activities.
    """
    serializer_class = TeamMemberActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter activities based on user's permissions."""
        user = self.request.user
        
        if user.is_platform_admin:
            return TeamMemberActivity.objects.all()
        
        if user.is_business_admin and user.tenant:
            return TeamMemberActivity.objects.filter(
                team_member__user__tenant=user.tenant
            )
        
        if user.is_manager:
            return TeamMemberActivity.objects.filter(
                Q(team_member__user=user) | Q(team_member__manager__user=user)
            )
        
        return TeamMemberActivity.objects.filter(team_member__user=user)

    def perform_create(self, serializer):
        """Create activity and update last login if it's a login activity."""
        activity = serializer.save()
        
        if activity.activity_type == 'login':
            activity.team_member.user.last_login = timezone.now()
            activity.team_member.user.save()


class TeamMemberPerformanceView(generics.ListCreateAPIView):
    """
    List and create team member performance records.
    """
    serializer_class = TeamMemberPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter performance records based on user's permissions."""
        user = self.request.user
        
        if user.is_platform_admin:
            return TeamMemberPerformance.objects.all()
        
        if user.is_business_admin and user.tenant:
            return TeamMemberPerformance.objects.filter(
                team_member__user__tenant=user.tenant
            )
        
        if user.is_manager:
            return TeamMemberPerformance.objects.filter(
                Q(team_member__user=user) | Q(team_member__manager__user=user)
            )
        
        return TeamMemberPerformance.objects.filter(team_member__user=user)


class TeamStatsView(APIView):
    """
    Get team statistics and analytics.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Calculate and return team statistics."""
        user = request.user
        
        # Get base queryset based on user permissions
        if user.is_platform_admin:
            team_members = TeamMember.objects.all()
        elif user.is_business_admin and user.tenant:
            team_members = TeamMember.objects.filter(user__tenant=user.tenant)
        elif user.is_manager:
            team_members = TeamMember.objects.filter(
                Q(user=user) | Q(manager__user=user)
            )
        else:
            team_members = TeamMember.objects.filter(user=user)
        
        # Calculate statistics
        total_members = team_members.count()
        active_members = team_members.filter(status='active').count()
        total_sales = team_members.aggregate(
            total=Sum('current_sales')
        )['total'] or 0
        
        # Calculate average performance
        performance_ratings = {
            'excellent': 5,
            'good': 4,
            'average': 3,
            'below_average': 2,
            'poor': 1
        }
        
        avg_performance = 0
        if total_members > 0:
            total_rating = 0
            for member in team_members:
                if member.performance_rating:
                    total_rating += performance_ratings.get(member.performance_rating, 3)
            avg_performance = total_rating / total_members
        
        # Get top performers
        top_performers = team_members.filter(
            performance_rating__in=['excellent', 'good']
        ).order_by('-current_sales')[:5]
        
        top_performers_data = []
        for member in top_performers:
            top_performers_data.append({
                'id': member.id,
                'name': member.user.get_full_name(),
                'role': member.user.get_role_display(),
                'sales': float(member.current_sales),
                'performance': member.performance_rating
            })
        
        # Get recent activities
        recent_activities = TeamMemberActivity.objects.filter(
            team_member__in=team_members
        ).order_by('-created_at')[:10]
        
        recent_activities_data = []
        for activity in recent_activities:
            recent_activities_data.append({
                'id': activity.id,
                'member_name': activity.team_member.user.get_full_name(),
                'activity_type': activity.get_activity_type_display(),
                'description': activity.description,
                'created_at': activity.created_at.isoformat()
            })
        
        # Prepare response data
        stats_data = {
            'total_members': total_members,
            'active_members': active_members,
            'total_sales': float(total_sales),
            'avg_performance': round(avg_performance, 2),
            'top_performers': top_performers_data,
            'recent_activities': recent_activities_data
        }
        
        serializer = TeamStatsSerializer(stats_data)
        return Response(serializer.data)


class TeamMemberSearchView(generics.ListAPIView):
    """
    Search team members by name, email, or role.
    """
    serializer_class = TeamMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = TeamMember.objects.all()

        # Filter by tenant
        if user.tenant:
            queryset = queryset.filter(user__tenant=user.tenant)

        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__role__icontains=search)
            )

        return queryset


class MessagingUsersView(generics.ListAPIView):
    """
    Get all users in the same tenant for messaging purposes.
    Returns user data in the format expected by the frontend.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        print(f"[MessagingUsersView] Current user: {user.username}, tenant: {user.tenant}")
        
        queryset = User.objects.filter(is_active=True)
        print(f"[MessagingUsersView] Initial queryset count: {queryset.count()}")
        
        # Filter by tenant
        if user.tenant:
            queryset = queryset.filter(tenant=user.tenant)
            print(f"[MessagingUsersView] After tenant filter count: {queryset.count()}")
        
        # Exclude the current user from the list
        queryset = queryset.exclude(id=user.id)
        print(f"[MessagingUsersView] After excluding current user count: {queryset.count()}")
        
        # Print some sample users
        sample_users = list(queryset[:3].values('username', 'first_name', 'last_name', 'role'))
        print(f"[MessagingUsersView] Sample users: {sample_users}")
        
        return queryset
    
    def get_serializer_class(self):
        return MessagingUserSerializer


class ManagerDashboardView(APIView):
    """
    Manager dashboard view providing overview data for managers.
    """
    permission_classes = [IsRoleAllowed.for_roles(['manager'])]

    def get(self, request):
        """Get manager dashboard data."""
        user = request.user
        
        # Check if user is authenticated
        if not user.is_authenticated:
            return Response({
                'error': 'Authentication required. Please log in.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Ensure user is a manager
        if not hasattr(user, 'is_manager') or not user.is_manager:
            return Response({
                'error': 'Access denied. Only managers can access this dashboard.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Get team members under this manager (if any)
            team_members = TeamMember.objects.filter(manager__user=user)
            total_team_members = team_members.count()
            active_members = team_members.filter(status='active').count()
            
            # Calculate total sales for the team
            total_team_sales = team_members.aggregate(
                total=Sum('current_sales')
            )['total'] or 0
            
            # Get recent activities (if any)
            recent_activities = TeamMemberActivity.objects.filter(
                team_member__in=team_members
            ).order_by('-created_at')[:5]
            
            # Get performance summary
            performance_summary = {
                'excellent': team_members.filter(performance_rating='excellent').count(),
                'good': team_members.filter(performance_rating='good').count(),
                'average': team_members.filter(performance_rating='average').count(),
                'below_average': team_members.filter(performance_rating='below_average').count(),
                'poor': team_members.filter(performance_rating='poor').count(),
            }
            
            # Get basic store statistics
            from apps.clients.models import Client
            from apps.escalation.models import Escalation
            
            # Get clients assigned to users in this manager's store
            if user.store:
                store_clients = Client.objects.filter(assigned_to__store=user.store)
                
                # Count leads (clients with no purchases)
                total_leads = store_clients.filter(purchases__isnull=True).distinct().count()
                
                # Count customers (clients with purchases)
                total_customers = store_clients.filter(purchases__isnull=False).distinct().count()
                
                # Count total sales (sum of all purchases)
                total_sales = store_clients.aggregate(
                    total_sales=Sum('purchases__amount')
                )['total_sales'] or 0
            else:
                total_leads = 0
                total_customers = 0
                total_sales = 0
            
            # Get escalations for this store
            if user.store:
                store_escalations = Escalation.objects.filter(
                    client__assigned_to__store=user.store
                )
                total_tasks = store_escalations.filter(status__in=['open', 'in_progress']).count()
            else:
                total_tasks = 0
            
            # Prepare response data
            dashboard_data = {
                'teamMembers': total_team_members,
                'leads': total_leads,
                'sales': float(total_sales),
                'tasks': total_tasks,
                'total_team_members': total_team_members,
                'active_members': active_members,
                'total_team_sales': float(total_team_sales),
                'performance_summary': performance_summary,
                'recent_activities': [
                    {
                        'id': activity.id,
                        'member_name': activity.team_member.user.get_full_name(),
                        'activity_type': activity.get_activity_type_display(),
                        'description': activity.description,
                        'created_at': activity.created_at.isoformat()
                    }
                    for activity in recent_activities
                ]
            }
            
            return Response(dashboard_data)
            
        except Exception as e:
            return Response({
                'error': f'Error loading dashboard data: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login view that works with existing users.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    print(f"Login attempt - Username: {username}, Password: {password}")
    
    if not username or not password:
        return Response({
            'error': 'Username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Try to authenticate with Django's built-in authentication
    user = authenticate(username=username, password=password)
    print(f"Authenticate result: {user}")
    
    if user is None:
        # If authentication fails, check if user exists and provide helpful error
        try:
            user = User.objects.get(username=username)
            print(f"User exists but password is incorrect: {user.username}")
            return Response({
                'error': 'Invalid password. Please check your password and try again.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            print(f"User not found: {username}")
            return Response({
                'error': 'User not found. Please check your username and try again.'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.is_active:
        print(f"User is inactive: {user.username}")
        return Response({
            'error': 'User account is disabled'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    print(f"Login successful for user: {user.username}")
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'success': True,
        'message': 'Login successful',
        'token': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'name': user.get_full_name() or user.username,
            'phone': user.phone,
            'address': user.address,
            'is_active': user.is_active,
            'tenant': user.tenant.id if user.tenant else None,
            'store': user.store.id if user.store else None,
            'tenant_name': user.tenant.name if user.tenant else None,
            'store_name': user.store.name if user.store else None,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Get current user profile.
    """
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'name': user.get_full_name() or user.username,
        'phone': user.phone,
        'address': user.address,
        'is_active': user.is_active,
        'tenant': user.tenant.id if user.tenant else None,
        'store': user.store.id if user.store else None,
        'tenant_name': user.tenant.name if user.tenant else None,
        'store_name': user.store.name if user.store else None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout view.
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'success': True,
            'message': 'Logout successful'
        })
    except Exception as e:
        return Response({
            'success': True,
            'message': 'Logout successful'
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def demo_users(request):
    """
    Get list of demo users for frontend testing.
    """
    users = User.objects.filter(is_active=True)[:10]
    demo_users = []
    
    for user in users:
        # Determine the correct password based on user role
        if user.role == 'platform_admin' or user.role == 'business_admin':
            password = 'admin123'
        else:
            password = 'password123'
            
        demo_users.append({
            'username': user.username,
            'password': password,
            'role': user.role,
            'name': user.get_full_name() or user.username,
            'email': user.email
        })
    
    return Response({
        'demo_users': demo_users
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def users_list(request):
    """
    Get list of users (for admin purposes).
    """
    users = User.objects.filter(is_active=True)
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def team_members_list(request):
    """
    Get list of team members filtered by tenant and store.
    """
    from .models import TeamMember
    from .serializers import TeamMemberListSerializer
    user = request.user
    
    print(f"team_members_list - User: {user.username}, Role: {user.role}, Tenant: {user.tenant}, Store: {user.store}")
    
    # Filter team members based on user's role, tenant, and store
    if user.is_platform_admin:
        # Platform admin can see all team members
        print("User is platform admin - showing all team members")
        team_members = TeamMember.objects.filter(user__is_active=True)
    elif user.is_business_admin and user.tenant:
        # Business admin can only see team members from their tenant
        print(f"User is business admin - filtering by tenant: {user.tenant}")
        team_members = TeamMember.objects.filter(user__is_active=True, user__tenant=user.tenant)
    elif user.is_manager and user.tenant and user.store:
        # Manager can see all team members in their store
        print(f"User is manager - filtering by tenant: {user.tenant} and store: {user.store}")
        team_members = TeamMember.objects.filter(user__is_active=True, user__tenant=user.tenant, user__store=user.store)
    elif user.is_manager and user.tenant:
        # Manager without specific store can see all team members in their tenant
        print(f"User is manager without store - filtering by tenant: {user.tenant}")
        team_members = TeamMember.objects.filter(user__is_active=True, user__tenant=user.tenant)
    else:
        # Other users can only see themselves
        print(f"User is other role - showing only self")
        team_members = TeamMember.objects.filter(user__is_active=True, user=user)
    
    print(f"Found {team_members.count()} team members")
    serializer = TeamMemberListSerializer(team_members, many=True)
    return Response(serializer.data)



