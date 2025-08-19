from rest_framework import serializers
from .models import Sale, SaleItem, SalesPipeline


class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = '__all__'


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = '__all__'


class SalesPipelineSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    sales_representative = serializers.SerializerMethodField()
    client_id = serializers.IntegerField(write_only=True, required=False)
    expected_close_date = serializers.DateField(required=False, allow_null=True)
    next_action_date = serializers.DateTimeField(required=False, allow_null=True)
    
    class Meta:
        model = SalesPipeline
        fields = [
            'id', 'title', 'client', 'client_id', 'sales_representative', 'stage', 'probability',
            'expected_value', 'actual_value', 'expected_close_date', 'actual_close_date',
            'notes', 'next_action', 'next_action_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'actual_close_date', 'actual_value']
    
    def get_client(self, obj):
        if obj.client:
            return {
                'id': obj.client.id,
                'first_name': obj.client.first_name,
                'last_name': obj.client.last_name,
                'full_name': obj.client.full_name,
            }
        return None
    

    
    def get_sales_representative(self, obj):
        if obj.sales_representative:
            return {
                'id': obj.sales_representative.id,
                'username': obj.sales_representative.username,
                'full_name': obj.sales_representative.get_full_name(),
            }
        return None
    
    def validate_client_id(self, value):
        """Validate that the client exists and belongs to the user's tenant"""
        from apps.clients.models import Client
        try:
            client = Client.objects.get(id=value, tenant=self.context['request'].user.tenant)
            return value
        except Client.DoesNotExist:
            raise serializers.ValidationError("Client not found or doesn't belong to your tenant.")
    
    def create(self, validated_data):
        """Create pipeline with proper client assignment"""
        print(f"SalesPipelineSerializer.create called with: {validated_data}")
        client_id = validated_data.pop('client_id', None)
        print(f"Client ID: {client_id}")
        if client_id:
            from apps.clients.models import Client
            try:
                validated_data['client'] = Client.objects.get(id=client_id)
                print(f"Client found: {validated_data['client']}")
            except Client.DoesNotExist:
                print(f"Client with ID {client_id} not found")
                raise serializers.ValidationError({"client_id": "Client not found."})
        else:
            print("No client_id provided")
            raise serializers.ValidationError({"client_id": "Client is required."})
        return super().create(validated_data)
