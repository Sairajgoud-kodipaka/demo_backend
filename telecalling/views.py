from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    CustomerVisit, Assignment, CallLog, FollowUp, 
    CustomerProfile, Notification, Analytics
)
from .serializers import (
    CustomerVisitSerializer, AssignmentSerializer, CallLogSerializer, FollowUpSerializer,
    CustomerProfileSerializer, NotificationSerializer, AnalyticsSerializer,
    BulkAssignmentSerializer, AssignmentStatsSerializer, DashboardDataSerializer
)

class CustomerVisitViewSet(viewsets.ModelViewSet):
    """Step 1: In-House Sales Rep records customer visit info"""
    queryset = CustomerVisit.objects.all()
    serializer_class = CustomerVisitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'inhouse_sales':
            # Sales reps see only their own visits
            return CustomerVisit.objects.filter(sales_rep=user)
        elif user.role == 'manager':
            # Managers see all visits from today
            today = timezone.now().date()
            return CustomerVisit.objects.filter(
                visit_timestamp__date=today,
                assigned_to_telecaller=False
            )
        elif user.role == 'tele_calling':
            # Telecallers see visits assigned to them
            return CustomerVisit.objects.filter(
                assignments__telecaller=user
            ).distinct()
        return CustomerVisit.objects.none()

    def perform_create(self, serializer):
        serializer.save(sales_rep=self.request.user)

    @action(detail=False, methods=['get'])
    def today_leads(self, request):
        """Get today's leads for manager assignment"""
        if request.user.role != 'manager':
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        today = timezone.now().date()
        leads = CustomerVisit.objects.filter(
            visit_timestamp__date=today,
            assigned_to_telecaller=False
        )
        serializer = self.get_serializer(leads, many=True)
        return Response(serializer.data)

class AssignmentViewSet(viewsets.ModelViewSet):
    """Step 2: Manager assigns leads to telecallers"""
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'manager':
            # Managers see all assignments
            return Assignment.objects.all()
        elif user.role == 'tele_calling':
            # Telecallers see only their assignments
            return Assignment.objects.filter(telecaller=user)
        return Assignment.objects.none()

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)
        # Mark customer visit as assigned
        customer_visit = serializer.instance.customer_visit
        customer_visit.assigned_to_telecaller = True
        customer_visit.save()
        
        # Create notification for telecaller
        Notification.objects.create(
            recipient=serializer.instance.telecaller,
            title="New Assignment",
            message=f"You have been assigned to call {customer_visit.customer_name}",
            notification_type='assignment',
            related_assignment=serializer.instance
        )

    @action(detail=False, methods=['post'])
    def bulk_assign(self, request):
        """Bulk assign leads to telecallers"""
        if request.user.role != 'manager':
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = BulkAssignmentSerializer(data=request.data)
        if serializer.is_valid():
            telecaller_ids = serializer.validated_data['telecaller_ids']
            customer_visit_ids = serializer.validated_data['customer_visit_ids']
            priority = serializer.validated_data['priority']
            notes = serializer.validated_data.get('notes', '')
            
            assignments_created = []
            for i, visit_id in enumerate(customer_visit_ids):
                telecaller_id = telecaller_ids[i % len(telecaller_ids)]
                try:
                    assignment = Assignment.objects.create(
                        telecaller_id=telecaller_id,
                        customer_visit_id=visit_id,
                        assigned_by=request.user,
                        priority=priority,
                        notes=notes
                    )
                    assignments_created.append(assignment)
                    
                    # Mark customer visit as assigned
                    customer_visit = assignment.customer_visit
                    customer_visit.assigned_to_telecaller = True
                    customer_visit.save()
                    
                    # Create notification
                    Notification.objects.create(
                        recipient_id=telecaller_id,
                        title="New Assignment",
                        message=f"You have been assigned to call {customer_visit.customer_name}",
                        notification_type='assignment',
                        related_assignment=assignment
                    )
                except Exception as e:
                    return Response({'error': f'Failed to create assignment: {str(e)}'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'message': f'Successfully created {len(assignments_created)} assignments',
                'assignments': AssignmentSerializer(assignments_created, many=True).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def detail_with_logs(self, request, pk=None):
        """Get assignment details with call logs"""
        try:
            assignment = self.get_object()
            serializer = self.get_serializer(assignment)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get assignment statistics"""
        user = request.user
        queryset = self.get_queryset()
        
        stats = {
            'total_assignments': queryset.count(),
            'completed_assignments': queryset.filter(status='completed').count(),
            'pending_assignments': queryset.filter(status='assigned').count(),
            'follow_up_assignments': queryset.filter(status='follow_up').count(),
            'total_calls': CallLog.objects.filter(assignment__in=queryset).count(),
            'conversions': CallLog.objects.filter(
                assignment__in=queryset,
                call_status='connected',
                customer_sentiment='positive'
            ).count(),
            'avg_call_duration': CallLog.objects.filter(
                assignment__in=queryset
            ).aggregate(avg=Avg('call_duration'))['avg'] or 0
        }
        
        if stats['total_calls'] > 0:
            stats['conversion_rate'] = (stats['conversions'] / stats['total_calls']) * 100
        else:
            stats['conversion_rate'] = 0
            
        return Response(stats)

class CallLogViewSet(viewsets.ModelViewSet):
    """Step 3: Telecaller logs call details and feedback"""
    queryset = CallLog.objects.all()
    serializer_class = CallLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'tele_calling':
            # Telecallers see only their call logs
            return CallLog.objects.filter(assignment__telecaller=user)
        elif user.role == 'manager':
            # Managers see all call logs
            return CallLog.objects.all()
        return CallLog.objects.none()

    def perform_create(self, serializer):
        call_log = serializer.save()
        
        # Update assignment status based on call outcome
        assignment = call_log.assignment
        if call_log.call_status == 'connected':
            assignment.status = 'completed'
        elif call_log.call_status in ['no_answer', 'busy', 'call_back']:
            assignment.status = 'follow_up'
        elif call_log.call_status == 'not_interested':
            assignment.status = 'completed'
        assignment.save()

        # Create notification for manager
        Notification.objects.create(
            recipient=assignment.assigned_by,
            title="Call Feedback Received",
            message=f"Feedback received for {assignment.customer_visit.customer_name}",
            notification_type='feedback',
            related_assignment=assignment
        )
        
        # Update customer profile
        self.update_customer_profile(call_log)

    def update_customer_profile(self, call_log):
        """Update customer profile with telecaller feedback"""
        assignment = call_log.assignment
        customer_visit = assignment.customer_visit
        
        profile, created = CustomerProfile.objects.get_or_create(
            customer_visit=customer_visit,
            defaults={
                'original_notes': customer_visit.notes,
                'telecaller_feedback': call_log.feedback,
                'last_contact_date': call_log.call_time,
                'engagement_score': self.calculate_engagement_score(call_log),
                'conversion_likelihood': self.calculate_conversion_likelihood(call_log)
            }
        )
        
        if not created:
            profile.telecaller_feedback = call_log.feedback
            profile.last_contact_date = call_log.call_time
            profile.engagement_score = self.calculate_engagement_score(call_log)
            profile.conversion_likelihood = self.calculate_conversion_likelihood(call_log)
            profile.save()

    def calculate_engagement_score(self, call_log):
        """Calculate engagement score based on call outcome and sentiment"""
        base_score = 50
        
        if call_log.call_status == 'connected':
            base_score += 30
        elif call_log.call_status == 'call_back':
            base_score += 20
        elif call_log.call_status == 'no_answer':
            base_score += 10
        
        if call_log.customer_sentiment == 'positive':
            base_score += 20
        elif call_log.customer_sentiment == 'neutral':
            base_score += 10
        elif call_log.customer_sentiment == 'negative':
            base_score -= 20
            
        return max(0, min(100, base_score))

    def calculate_conversion_likelihood(self, call_log):
        """Calculate conversion likelihood based on call outcome"""
        if call_log.call_status == 'connected' and call_log.customer_sentiment == 'positive':
            return 'very_high'
        elif call_log.call_status == 'connected' and call_log.customer_sentiment == 'neutral':
            return 'high'
        elif call_log.call_status == 'call_back':
            return 'medium'
        elif call_log.call_status == 'not_interested':
            return 'very_low'
        else:
            return 'low'

class FollowUpViewSet(viewsets.ModelViewSet):
    """Step 4: Manager monitors and creates follow-ups"""
    queryset = FollowUp.objects.all()
    serializer_class = FollowUpSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'manager':
            # Managers see all follow-ups
            return FollowUp.objects.all()
        elif user.role == 'tele_calling':
            # Telecallers see follow-ups for their assignments
            return FollowUp.objects.filter(assignment__telecaller=user)
        return FollowUp.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        
        # Create notification for telecaller
        follow_up = serializer.instance
        Notification.objects.create(
            recipient=follow_up.assignment.telecaller,
            title="Follow-up Scheduled",
            message=f"Follow-up scheduled for {follow_up.assignment.customer_visit.customer_name}",
            notification_type='follow_up',
            related_assignment=follow_up.assignment
        )

    @action(detail=False, methods=['get'])
    def high_potential_leads(self, request):
        """Get high potential leads for follow-up"""
        if request.user.role != 'manager':
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get assignments with positive sentiment but no conversion
        high_potential = Assignment.objects.filter(
            call_logs__customer_sentiment='positive',
            call_logs__call_status='connected',
            status='follow_up'
        ).distinct()
        
        serializer = AssignmentSerializer(high_potential, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def unconnected_calls(self, request):
        """Get unconnected calls for follow-up"""
        if request.user.role != 'manager':
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        unconnected = Assignment.objects.filter(
            call_logs__call_status__in=['no_answer', 'busy', 'call_back']
        ).distinct()
        
        serializer = AssignmentSerializer(unconnected, many=True)
        return Response(serializer.data)

class CustomerProfileViewSet(viewsets.ModelViewSet):
    """Step 5: Enhanced customer profile with sales rep notes + telecaller feedback"""
    queryset = CustomerProfile.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'inhouse_sales':
            # Sales reps see profiles for their visits
            return CustomerProfile.objects.filter(customer_visit__sales_rep=user)
        elif user.role == 'manager':
            # Managers see all profiles
            return CustomerProfile.objects.all()
        elif user.role == 'tele_calling':
            # Telecallers see profiles for their assignments
            return CustomerProfile.objects.filter(
                customer_visit__assignments__telecaller=user
            ).distinct()
        return CustomerProfile.objects.none()

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get customer profile analytics"""
        user = request.user
        queryset = self.get_queryset()
        
        analytics = {
            'total_profiles': queryset.count(),
            'high_engagement': queryset.filter(engagement_score__gte=80).count(),
            'medium_engagement': queryset.filter(
                engagement_score__gte=50, engagement_score__lt=80
            ).count(),
            'low_engagement': queryset.filter(engagement_score__lt=50).count(),
            'avg_engagement_score': queryset.aggregate(avg=Avg('engagement_score'))['avg'] or 0,
            'conversion_likelihood_distribution': {
                'very_high': queryset.filter(conversion_likelihood='very_high').count(),
                'high': queryset.filter(conversion_likelihood='high').count(),
                'medium': queryset.filter(conversion_likelihood='medium').count(),
                'low': queryset.filter(conversion_likelihood='low').count(),
                'very_low': queryset.filter(conversion_likelihood='very_low').count(),
            }
        }
        
        return Response(analytics)

class NotificationViewSet(viewsets.ModelViewSet):
    """Notification system for assignments and feedback alerts"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all marked as read'})

class AnalyticsViewSet(viewsets.ModelViewSet):
    """Analytics tracking for conversion rates and performance metrics"""
    queryset = Analytics.objects.all()
    serializer_class = AnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['manager', 'tele_calling']:
            return Analytics.objects.all()
        return Analytics.objects.none()

    @action(detail=False, methods=['get'])
    def dashboard_data(self, request):
        """Get dashboard data for different roles"""
        user = request.user
        
        if user.role == 'manager':
            today = timezone.now().date()
            data = {
                'today_leads': CustomerVisit.objects.filter(
                    visit_timestamp__date=today
                ).count(),
                'pending_assignments': Assignment.objects.filter(
                    status='assigned'
                ).count(),
                'completed_calls': CallLog.objects.filter(
                    call_status='connected'
                ).count(),
                'high_potential_leads': Assignment.objects.filter(
                    call_logs__customer_sentiment='positive',
                    status='follow_up'
                ).distinct().count(),
                'unconnected_calls': CallLog.objects.filter(
                    call_status__in=['no_answer', 'busy', 'call_back']
                ).count(),
                'recent_activities': self.get_recent_activities(),
                'performance_metrics': self.get_performance_metrics()
            }
        elif user.role == 'tele_calling':
            data = {
                'my_assignments': Assignment.objects.filter(telecaller=user).count(),
                'completed_calls': CallLog.objects.filter(
                    assignment__telecaller=user,
                    call_status='connected'
                ).count(),
                'pending_followups': FollowUp.objects.filter(
                    assignment__telecaller=user,
                    status='pending'
                ).count(),
                'conversion_rate': self.calculate_telecaller_conversion_rate(user),
                'recent_activities': self.get_telecaller_activities(user)
            }
        else:
            data = {}
        
        return Response(data)

    def get_recent_activities(self):
        """Get recent activities for manager dashboard"""
        activities = []
        
        # Recent assignments
        recent_assignments = Assignment.objects.select_related(
            'telecaller', 'customer_visit'
        ).order_by('-created_at')[:5]
        
        for assignment in recent_assignments:
            activities.append({
                'type': 'assignment',
                'description': f"Assigned {assignment.customer_visit.customer_name} to {assignment.telecaller.get_full_name()}",
                'timestamp': assignment.created_at,
                'user': assignment.assigned_by.get_full_name()
            })
        
        # Recent call logs
        recent_calls = CallLog.objects.select_related(
            'assignment__telecaller', 'assignment__customer_visit'
        ).order_by('-call_time')[:5]
        
        for call in recent_calls:
            activities.append({
                'type': 'call',
                'description': f"Call to {call.assignment.customer_visit.customer_name} - {call.call_status}",
                'timestamp': call.call_time,
                'user': call.assignment.telecaller.get_full_name()
            })
        
        # Sort by timestamp and return top 10
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:10]

    def get_performance_metrics(self):
        """Get performance metrics for manager dashboard"""
        today = timezone.now().date()
        
        return {
            'total_leads_today': CustomerVisit.objects.filter(
                visit_timestamp__date=today
            ).count(),
            'assigned_leads_today': Assignment.objects.filter(
                created_at__date=today
            ).count(),
            'conversion_rate': self.calculate_overall_conversion_rate(),
            'avg_call_duration': CallLog.objects.aggregate(
                avg=Avg('call_duration')
            )['avg'] or 0
        }

    def calculate_overall_conversion_rate(self):
        """Calculate overall conversion rate"""
        total_calls = CallLog.objects.filter(call_status='connected').count()
        conversions = CallLog.objects.filter(
            call_status='connected',
            customer_sentiment='positive'
        ).count()
        
        if total_calls > 0:
            return (conversions / total_calls) * 100
        return 0

    def calculate_telecaller_conversion_rate(self, telecaller):
        """Calculate conversion rate for specific telecaller"""
        total_calls = CallLog.objects.filter(
            assignment__telecaller=telecaller,
            call_status='connected'
        ).count()
        
        conversions = CallLog.objects.filter(
            assignment__telecaller=telecaller,
            call_status='connected',
            customer_sentiment='positive'
        ).count()
        
        if total_calls > 0:
            return (conversions / total_calls) * 100
        return 0

    def get_telecaller_activities(self, telecaller):
        """Get recent activities for telecaller"""
        activities = []
        
        # Recent call logs
        recent_calls = CallLog.objects.filter(
            assignment__telecaller=telecaller
        ).select_related('assignment__customer_visit').order_by('-call_time')[:5]
        
        for call in recent_calls:
            activities.append({
                'type': 'call',
                'description': f"Call to {call.assignment.customer_visit.customer_name} - {call.call_status}",
                'timestamp': call.call_time
            })
        
        return activities
