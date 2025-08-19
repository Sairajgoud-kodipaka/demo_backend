from rest_framework import serializers
from .models import Store, StoreUserMap

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = '__all__'
        read_only_fields = ('created_at', 'tenant')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            # Only set tenant if not provided (platform admin can set it)
            if not validated_data.get('tenant'):
                validated_data['tenant'] = user.tenant
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Prevent tenant from being changed after creation
        validated_data.pop('tenant', None)
        return super().update(instance, validated_data)

class StoreUserMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreUserMap
        fields = '__all__'
        read_only_fields = ('created_at',) 