from rest_framework import generics, permissions, status, filters, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django_filters.rest_framework import DjangoFilterBackend
from .models import Feedback, FeedbackResponse, FeedbackSurvey, FeedbackQuestion, FeedbackSubmission
from .serializers import (
    FeedbackSerializer, FeedbackCreateSerializer, FeedbackUpdateSerializer,
    FeedbackResponseSerializer, FeedbackResponseCreateSerializer,
    FeedbackSurveySerializer, FeedbackSurveyCreateSerializer,
    FeedbackQuestionSerializer, FeedbackQuestionCreateSerializer,
    FeedbackSubmissionSerializer, FeedbackSubmissionCreateSerializer,
    FeedbackStatsSerializer, FeedbackSurveyStatsSerializer
)
from apps.users.permissions import IsRoleAllowed


class FeedbackListView(generics.ListCreateAPIView):
    """
    List and create feedback.
    """
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'category', 'sentiment', 'is_public']
    search_fields = ['title', 'content', 'client__first_name', 'client__last_name', 'client__email']
    ordering_fields = ['created_at', 'updated_at', 'overall_rating']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return Feedback.objects.all()
        elif user.is_business_admin:
            return Feedback.objects.filter(tenant=user.tenant)
        else:
            return Feedback.objects.filter(tenant=user.tenant)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FeedbackCreateSerializer
        return FeedbackSerializer


class FeedbackDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete feedback.
    """
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return Feedback.objects.all()
        elif user.is_business_admin:
            return Feedback.objects.filter(tenant=user.tenant)
        else:
            return Feedback.objects.filter(tenant=user.tenant)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return FeedbackUpdateSerializer
        return FeedbackSerializer


class FeedbackActionsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for feedback actions like mark_reviewed and escalate.
    """
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['post']  # Only allow POST for actions

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return Feedback.objects.all()
        elif user.is_business_admin:
            return Feedback.objects.filter(tenant=user.tenant)
        else:
            return Feedback.objects.filter(tenant=user.tenant)

    @action(detail=True, methods=['post'])
    def mark_reviewed(self, request, pk=None):
        """Mark feedback as reviewed."""
        feedback = self.get_object()
        feedback.status = Feedback.Status.REVIEWED
        feedback.reviewed_by = request.user
        feedback.save()
        return Response({'message': 'Feedback marked as reviewed'})

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Escalate feedback to escalation system."""
        feedback = self.get_object()
        feedback.status = Feedback.Status.ESCALATED
        feedback.save()
        
        # Create escalation from feedback
        from apps.escalation.models import Escalation
        escalation = Escalation.objects.create(
            title=f"Escalated Feedback: {feedback.title}",
            description=feedback.content,
            category=Escalation.Category.COMPLAINT if feedback.overall_rating <= 2 else Escalation.Category.OTHER,
            priority=Escalation.Priority.HIGH if feedback.overall_rating <= 2 else Escalation.Priority.MEDIUM,
            client=feedback.client,
            created_by=request.user,
            tenant=request.user.tenant
        )
        
        return Response({
            'message': 'Feedback escalated successfully',
            'escalation_id': escalation.id
        })


class FeedbackResponseListView(generics.ListCreateAPIView):
    """
    List and create responses for feedback.
    """
    serializer_class = FeedbackResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        feedback_id = self.kwargs.get('feedback_id')
        return FeedbackResponse.objects.filter(feedback_id=feedback_id)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FeedbackResponseCreateSerializer
        return FeedbackResponseSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.context['feedback_id'] = self.kwargs.get('feedback_id')
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FeedbackResponseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete a feedback response.
    """
    serializer_class = FeedbackResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        feedback_id = self.kwargs.get('feedback_id')
        return FeedbackResponse.objects.filter(feedback_id=feedback_id)


class FeedbackSurveyListView(generics.ListCreateAPIView):
    """
    List and create feedback surveys.
    """
    serializer_class = FeedbackSurveySerializer
    permission_classes = [IsRoleAllowed.for_roles(['manager', 'business_admin', 'platform_admin'])]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['survey_type', 'is_active']

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return FeedbackSurvey.objects.all()
        return FeedbackSurvey.objects.filter(tenant=user.tenant)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant=request.user.tenant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FeedbackSurveyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete a feedback survey.
    """
    serializer_class = FeedbackSurveySerializer
    permission_classes = [IsRoleAllowed.for_roles(['manager', 'business_admin', 'platform_admin'])]

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return FeedbackSurvey.objects.all()
        return FeedbackSurvey.objects.filter(tenant=user.tenant)


class FeedbackQuestionListView(generics.ListCreateAPIView):
    """
    List and create questions for a survey.
    """
    serializer_class = FeedbackQuestionSerializer
    permission_classes = [IsRoleAllowed.for_roles(['manager', 'business_admin', 'platform_admin'])]

    def get_queryset(self):
        survey_id = self.kwargs.get('survey_id')
        return FeedbackQuestion.objects.filter(survey_id=survey_id)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FeedbackQuestionCreateSerializer
        return FeedbackQuestionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.context['survey_id'] = self.kwargs.get('survey_id')
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FeedbackQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete a survey question.
    """
    serializer_class = FeedbackQuestionSerializer
    permission_classes = [IsRoleAllowed.for_roles(['manager', 'business_admin', 'platform_admin'])]

    def get_queryset(self):
        survey_id = self.kwargs.get('survey_id')
        return FeedbackQuestion.objects.filter(survey_id=survey_id)


class FeedbackSubmissionListView(generics.ListCreateAPIView):
    """
    List and create survey submissions.
    """
    serializer_class = FeedbackSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        survey_id = self.kwargs.get('survey_id')
        return FeedbackSubmission.objects.filter(survey_id=survey_id)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FeedbackSubmissionCreateSerializer
        return FeedbackSubmissionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.context['survey_id'] = self.kwargs.get('survey_id')
        serializer.context['client_id'] = request.data.get('client_id')
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FeedbackSubmissionDetailView(generics.RetrieveAPIView):
    """
    Retrieve a survey submission.
    """
    serializer_class = FeedbackSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        survey_id = self.kwargs.get('survey_id')
        return FeedbackSubmission.objects.filter(survey_id=survey_id)


class FeedbackStatsView(generics.GenericAPIView):
    """
    Get feedback statistics.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            print(f"Stats request from user: {user.username}, tenant: {getattr(user, 'tenant', None)}")
            
            # Base queryset - handle tenant filtering properly
            if user.is_platform_admin:
                queryset = Feedback.objects.all()
            elif hasattr(user, 'tenant') and user.tenant:
                queryset = Feedback.objects.filter(tenant=user.tenant)
            else:
                # If user has no tenant, show all feedback (or you could show none)
                queryset = Feedback.objects.all()

            print(f"Queryset count: {queryset.count()}")
            print(f"All feedback count: {Feedback.objects.count()}")

            # Calculate statistics with error handling
            total_feedback = queryset.count()
            positive_feedback = queryset.filter(overall_rating__gte=4).count()
            negative_feedback = queryset.filter(overall_rating__lte=2).count()
            neutral_feedback = queryset.filter(overall_rating=3).count()
            
            print(f"Stats calculated: total={total_feedback}, positive={positive_feedback}, negative={negative_feedback}, neutral={neutral_feedback}")
            
            avg_overall_rating = queryset.aggregate(
                avg_rating=Avg('overall_rating')
            )['avg_rating'] or 0

            # Breakdowns with error handling
            try:
                feedback_by_category = dict(queryset.values_list('category').annotate(count=Count('id')))
            except Exception as e:
                print(f"Error in category breakdown: {e}")
                feedback_by_category = {}
                
            try:
                feedback_by_status = dict(queryset.values_list('status').annotate(count=Count('id')))
            except Exception as e:
                print(f"Error in status breakdown: {e}")
                feedback_by_status = {}
                
            try:
                feedback_by_sentiment = dict(queryset.values_list('sentiment').annotate(count=Count('id')))
            except Exception as e:
                print(f"Error in sentiment breakdown: {e}")
                feedback_by_sentiment = {}

            # Recent feedback with error handling
            try:
                recent_feedback = list(queryset.order_by('-created_at')[:5].values(
                    'id', 'title', 'overall_rating', 'created_at', 'client__first_name', 'client__last_name'
                ))
                # Format the client name properly
                for feedback in recent_feedback:
                    first_name = feedback.get('client__first_name', '')
                    last_name = feedback.get('client__last_name', '')
                    feedback['client_name'] = f"{first_name} {last_name}".strip()
                    # Remove the individual name fields to keep the response clean
                    feedback.pop('client__first_name', None)
                    feedback.pop('client__last_name', None)
            except Exception as e:
                print(f"Error in recent feedback: {e}")
                recent_feedback = []

            # Top issues (negative feedback categories) with error handling
            try:
                top_issues = list(queryset.filter(overall_rating__lte=2).values('category').annotate(
                    count=Count('id')
                ).order_by('-count')[:5])
            except Exception as e:
                print(f"Error in top issues: {e}")
                top_issues = []

            stats = {
                'total_feedback': total_feedback,
                'positive_feedback': positive_feedback,
                'negative_feedback': negative_feedback,
                'neutral_feedback': neutral_feedback,
                'avg_overall_rating': round(avg_overall_rating, 2),
                'feedback_by_category': feedback_by_category,
                'feedback_by_status': feedback_by_status,
                'feedback_by_sentiment': feedback_by_sentiment,
                'recent_feedback': recent_feedback,
                'top_issues': top_issues,
            }

            serializer = FeedbackStatsSerializer(stats)
            return Response(serializer.data)
            
        except Exception as e:
            print(f"Error in FeedbackStatsView: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {
                    'error': 'Failed to fetch feedback statistics',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FeedbackSurveyStatsView(generics.GenericAPIView):
    """
    Get feedback survey statistics.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Base queryset
        if user.is_platform_admin:
            survey_queryset = FeedbackSurvey.objects.all()
            submission_queryset = FeedbackSubmission.objects.all()
        else:
            survey_queryset = FeedbackSurvey.objects.filter(tenant=user.tenant)
            submission_queryset = FeedbackSubmission.objects.filter(survey__tenant=user.tenant)

        # Calculate statistics
        total_surveys = survey_queryset.count()
        active_surveys = survey_queryset.filter(is_active=True).count()
        total_submissions = submission_queryset.count()
        
        # Average completion rate
        surveys_with_submissions = survey_queryset.annotate(
            submission_count=Count('submissions')
        ).filter(submission_count__gt=0)
        
        avg_completion_rate = surveys_with_submissions.aggregate(
            avg_rate=Avg('submission_count')
        )['avg_rate'] or 0

        # Breakdowns
        surveys_by_type = dict(survey_queryset.values_list('survey_type').annotate(count=Count('id')))

        # Recent submissions
        recent_submissions = list(submission_queryset.order_by('-submitted_at')[:10].values(
            'id', 'survey__name', 'client__first_name', 'client__last_name', 'submitted_at'
        ))
        # Format the client name properly
        for submission in recent_submissions:
            first_name = submission.get('client__first_name', '')
            last_name = submission.get('client__last_name', '')
            submission['client_name'] = f"{first_name} {last_name}".strip()
            # Remove the individual name fields to keep the response clean
            submission.pop('client__first_name', None)
            submission.pop('client__last_name', None)

        stats = {
            'total_surveys': total_surveys,
            'active_surveys': active_surveys,
            'total_submissions': total_submissions,
            'avg_completion_rate': round(avg_completion_rate, 2),
            'surveys_by_type': surveys_by_type,
            'recent_submissions': recent_submissions,
        }

        serializer = FeedbackSurveyStatsSerializer(stats)
        return Response(serializer.data)


class PublicFeedbackView(generics.ListAPIView):
    """
    Get public feedback for display.
    """
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['category', 'sentiment']
    ordering_fields = ['created_at', 'overall_rating']
    ordering = ['-created_at']

    def get_queryset(self):
        return Feedback.objects.filter(
            is_public=True,
            status__in=['reviewed', 'actioned', 'closed']
        )


class SubmitFeedbackView(generics.CreateAPIView):
    """
    Public endpoint for submitting feedback.
    """
    serializer_class = FeedbackCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # For public submissions, we need to handle tenant differently
        # This could be based on a tenant identifier in the request
        tenant_id = request.data.get('tenant_id')
        if tenant_id:
            from apps.tenants.models import Tenant
            try:
                tenant = Tenant.objects.get(id=tenant_id)
                serializer.save(tenant=tenant)
            except Tenant.DoesNotExist:
                return Response({'error': 'Invalid tenant'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'Tenant ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
