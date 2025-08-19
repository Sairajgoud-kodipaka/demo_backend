from rest_framework import generics, permissions, status, filters, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django_filters.rest_framework import DjangoFilterBackend
from .models import Escalation, EscalationNote, EscalationTemplate
from .serializers import (
    EscalationSerializer, EscalationCreateSerializer, EscalationUpdateSerializer,
    EscalationNoteSerializer, EscalationNoteCreateSerializer,
    EscalationTemplateSerializer, EscalationStatsSerializer
)
from apps.users.permissions import IsRoleAllowed


class EscalationListView(generics.ListCreateAPIView):
    """
    List and create escalations.
    """
    serializer_class = EscalationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'category', 'assigned_to']
    search_fields = ['title', 'description', 'client__name']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'due_date']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return Escalation.objects.all()
        elif user.is_business_admin:
            return Escalation.objects.filter(tenant=user.tenant)
        elif user.is_manager:
            # Store managers should see all escalations from their store
            if user.store:
                return Escalation.objects.filter(
                    Q(tenant=user.tenant) & 
                    Q(client__assigned_to__store=user.store)
                )
            else:
                return Escalation.objects.filter(
                    Q(tenant=user.tenant) & 
                    (Q(assigned_to=user) | Q(assigned_to__isnull=True))
                )
        else:
            return Escalation.objects.filter(
                Q(tenant=user.tenant) & 
                (Q(created_by=user) | Q(assigned_to=user))
            )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EscalationCreateSerializer
        return EscalationSerializer


class EscalationDetailView(viewsets.ModelViewSet):
    """
    Retrieve, update, and delete an escalation.
    """
    serializer_class = EscalationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'put', 'patch', 'delete', 'post']  # Allow POST for actions

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return Escalation.objects.all()
        elif user.is_business_admin:
            return Escalation.objects.filter(tenant=user.tenant)
        elif user.is_manager:
            # Store managers should see all escalations from their store
            if user.store:
                return Escalation.objects.filter(
                    Q(tenant=user.tenant) & 
                    Q(client__assigned_to__store=user.store)
                )
            else:
                return Escalation.objects.filter(
                    Q(tenant=user.tenant) & 
                    (Q(assigned_to=user) | Q(assigned_to__isnull=True))
                )
        else:
            return Escalation.objects.filter(
                Q(tenant=user.tenant) & 
                (Q(created_by=user) | Q(assigned_to=user))
            )

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return EscalationUpdateSerializer
        return EscalationSerializer

    @action(detail=True, methods=['post'])
    def assign_to_me(self, request, pk=None):
        """Assign escalation to current user."""
        escalation = self.get_object()
        escalation.assigned_to = request.user
        escalation.assigned_at = timezone.now()
        escalation.status = Escalation.Status.IN_PROGRESS
        escalation.save()
        return Response({'message': 'Escalation assigned successfully'})

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Change escalation status."""
        escalation = self.get_object()
        new_status = request.data.get('status')
        if new_status in dict(Escalation.Status.choices):
            escalation.status = new_status
            escalation.save()
            return Response({'message': 'Status updated successfully'})
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign escalation to a user."""
        escalation = self.get_object()
        assigned_to_id = request.data.get('assigned_to')
        if assigned_to_id:
            from apps.users.models import User
            try:
                assigned_user = User.objects.get(id=assigned_to_id)
                escalation.assigned_to = assigned_user
                escalation.assigned_at = timezone.now()
                escalation.status = Escalation.Status.IN_PROGRESS
                escalation.save()
                return Response({'message': 'Escalation assigned successfully'})
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'assigned_to is required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve escalation."""
        escalation = self.get_object()
        escalation.status = Escalation.Status.RESOLVED
        escalation.resolved_at = timezone.now()
        escalation.save()
        return Response({'message': 'Escalation resolved successfully'})

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close escalation."""
        escalation = self.get_object()
        escalation.status = Escalation.Status.CLOSED
        escalation.closed_at = timezone.now()
        escalation.save()
        return Response({'message': 'Escalation closed successfully'})


class EscalationNoteListView(generics.ListCreateAPIView):
    """
    List and create notes for an escalation.
    """
    serializer_class = EscalationNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        escalation_id = self.kwargs.get('escalation_id')
        return EscalationNote.objects.filter(escalation_id=escalation_id)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EscalationNoteCreateSerializer
        return EscalationNoteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.context['escalation_id'] = self.kwargs.get('escalation_id')
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EscalationNoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete an escalation note.
    """
    serializer_class = EscalationNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        escalation_id = self.kwargs.get('escalation_id')
        return EscalationNote.objects.filter(escalation_id=escalation_id)


class EscalationTemplateListView(generics.ListCreateAPIView):
    """
    List and create escalation templates.
    """
    serializer_class = EscalationTemplateSerializer
    permission_classes = [IsRoleAllowed.for_roles(['manager', 'business_admin', 'platform_admin'])]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'is_active']

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return EscalationTemplate.objects.all()
        return EscalationTemplate.objects.filter(tenant=user.tenant)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant=request.user.tenant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EscalationTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete an escalation template.
    """
    serializer_class = EscalationTemplateSerializer
    permission_classes = [IsRoleAllowed.for_roles(['manager', 'business_admin', 'platform_admin'])]

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return EscalationTemplate.objects.all()
        return EscalationTemplate.objects.filter(tenant=user.tenant)


class EscalationStatsView(generics.GenericAPIView):
    """
    Get escalation statistics.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            
            # Base queryset
            if user.is_platform_admin:
                queryset = Escalation.objects.all()
            elif user.is_business_admin:
                queryset = Escalation.objects.filter(tenant=user.tenant)
            elif user.is_manager:
                # Store managers should see all escalations from their store
                if user.store:
                    queryset = Escalation.objects.filter(
                        Q(tenant=user.tenant) & 
                        Q(client__assigned_to__store=user.store)
                    )
                else:
                    queryset = Escalation.objects.filter(
                        Q(tenant=user.tenant) & 
                        (Q(assigned_to=user) | Q(assigned_to__isnull=True))
                    )
            else:
                queryset = Escalation.objects.filter(
                    Q(tenant=user.tenant) & 
                    (Q(created_by=user) | Q(assigned_to=user))
                )

            # Calculate basic statistics
            total_escalations = queryset.count()
            open_escalations = queryset.filter(status__in=['open', 'in_progress', 'pending_customer']).count()
            
            # Count overdue escalations
            overdue_escalations = 0
            for escalation in queryset:
                if escalation.is_overdue:
                    overdue_escalations += 1
            
            # Resolved today
            today = timezone.now().date()
            resolved_today = queryset.filter(
                status__in=['resolved', 'closed'],
                resolved_at__date=today
            ).count()

            # Average resolution time
            resolved_escalations = queryset.filter(status__in=['resolved', 'closed'])
            total_resolution_time = 0
            resolved_count = 0
            
            for escalation in resolved_escalations:
                if escalation.time_to_resolution is not None:
                    total_resolution_time += escalation.time_to_resolution
                    resolved_count += 1
            
            avg_resolution_time = (total_resolution_time / resolved_count) if resolved_count > 0 else 0

            # SLA compliance rate
            sla_compliant = 0
            for escalation in resolved_escalations:
                if escalation.sla_compliance:
                    sla_compliant += 1
            
            sla_compliance_rate = (sla_compliant / resolved_count * 100) if resolved_count > 0 else 0

            # Breakdowns
            escalations_by_priority = {}
            escalations_by_category = {}
            escalations_by_status = {}
            
            for priority, _ in Escalation.Priority.choices:
                count = queryset.filter(priority=priority).count()
                escalations_by_priority[priority] = count
                
            for category, _ in Escalation.Category.choices:
                count = queryset.filter(category=category).count()
                escalations_by_category[category] = count
                
            for status, _ in Escalation.Status.choices:
                count = queryset.filter(status=status).count()
                escalations_by_status[status] = count

            stats = {
                'total_escalations': total_escalations,
                'open_escalations': open_escalations,
                'overdue_escalations': overdue_escalations,
                'resolved_today': resolved_today,
                'avg_resolution_time': round(avg_resolution_time, 2),
                'sla_compliance_rate': round(sla_compliance_rate, 2),
                'escalations_by_priority': escalations_by_priority,
                'escalations_by_category': escalations_by_category,
                'escalations_by_status': escalations_by_status,
            }

            serializer = EscalationStatsSerializer(stats)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Error calculating stats: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MyEscalationsView(generics.ListAPIView):
    """
    Get escalations assigned to the current user.
    """
    serializer_class = EscalationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'category']
    search_fields = ['title', 'description', 'client__name']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'due_date']
    ordering = ['-created_at']

    def get_queryset(self):
        return Escalation.objects.filter(
            Q(assigned_to=self.request.user) | Q(created_by=self.request.user)
        ).filter(tenant=self.request.user.tenant)
