from rest_framework import serializers
from .models import Feedback, FeedbackResponse, FeedbackSurvey, FeedbackQuestion, FeedbackSubmission
from apps.users.serializers import UserSerializer
from apps.clients.serializers import ClientSerializer


class FeedbackResponseSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = FeedbackResponse
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class FeedbackQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackQuestion
        fields = '__all__'
        read_only_fields = ('created_at',)


class FeedbackSurveySerializer(serializers.ModelSerializer):
    questions = FeedbackQuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = FeedbackSurvey
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class FeedbackSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackSubmission
        fields = '__all__'
        read_only_fields = ('submitted_at',)


class FeedbackSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    submitted_by = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)
    responses = FeedbackResponseSerializer(many=True, read_only=True)
    average_rating = serializers.ReadOnlyField()
    is_positive_feedback = serializers.ReadOnlyField()
    is_negative_feedback = serializers.ReadOnlyField()
    
    class Meta:
        model = Feedback
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'reviewed_at', 'actioned_at', 'sentiment', 'sentiment_score')

    def create(self, validated_data):
        # Set the submitted_by field to the current user if not provided
        if 'submitted_by' not in validated_data:
            validated_data['submitted_by'] = self.context['request'].user
        validated_data['tenant'] = self.context['request'].user.tenant
        return super().create(validated_data)


class FeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['title', 'content', 'category', 'overall_rating', 'product_rating', 
                 'service_rating', 'value_rating', 'client', 'is_anonymous', 'is_public', 'tags']

    def create(self, validated_data):
        validated_data['submitted_by'] = self.context['request'].user
        
        # Handle tenant assignment
        user = self.context['request'].user
        if user.tenant:
            validated_data['tenant'] = user.tenant
        else:
            # If user has no tenant, try to get the first available tenant
            from apps.tenants.models import Tenant
            try:
                default_tenant = Tenant.objects.first()
                if default_tenant:
                    validated_data['tenant'] = default_tenant
                else:
                    raise serializers.ValidationError("No tenant available for feedback creation")
            except Exception as e:
                raise serializers.ValidationError("Unable to assign tenant for feedback")
        
        return super().create(validated_data)


class FeedbackUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['title', 'content', 'category', 'status', 'overall_rating', 
                 'product_rating', 'service_rating', 'value_rating', 'is_public', 'tags']


class FeedbackResponseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackResponse
        fields = ['content', 'is_public']

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['feedback_id'] = self.context['feedback_id']
        return super().create(validated_data)


class FeedbackSurveyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackSurvey
        fields = ['name', 'description', 'survey_type']

    def create(self, validated_data):
        validated_data['tenant'] = self.context['request'].user.tenant
        return super().create(validated_data)


class FeedbackQuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackQuestion
        fields = ['question_text', 'question_type', 'is_required', 'order', 'options']

    def create(self, validated_data):
        validated_data['survey_id'] = self.context['survey_id']
        return super().create(validated_data)


class FeedbackSubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackSubmission
        fields = ['answers']

    def create(self, validated_data):
        validated_data['survey_id'] = self.context['survey_id']
        validated_data['client_id'] = self.context['client_id']
        validated_data['ip_address'] = self.context['request'].META.get('REMOTE_ADDR')
        validated_data['user_agent'] = self.context['request'].META.get('HTTP_USER_AGENT', '')
        return super().create(validated_data)


class FeedbackStatsSerializer(serializers.Serializer):
    total_feedback = serializers.IntegerField()
    positive_feedback = serializers.IntegerField()
    negative_feedback = serializers.IntegerField()
    neutral_feedback = serializers.IntegerField()
    avg_overall_rating = serializers.FloatField()
    feedback_by_category = serializers.DictField()
    feedback_by_status = serializers.DictField()
    feedback_by_sentiment = serializers.DictField()
    recent_feedback = serializers.ListField()
    top_issues = serializers.ListField()


class FeedbackSurveyStatsSerializer(serializers.Serializer):
    total_surveys = serializers.IntegerField()
    active_surveys = serializers.IntegerField()
    total_submissions = serializers.IntegerField()
    avg_completion_rate = serializers.FloatField()
    surveys_by_type = serializers.DictField()
    recent_submissions = serializers.ListField() 