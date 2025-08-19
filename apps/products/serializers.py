from rest_framework import serializers
from .models import Product, Category, ProductVariant, ProductInventory, StockTransfer


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'updated_at']
    
    def get_product_count(self, obj):
        return obj.products.count()
    
    def create(self, validated_data):
        user = self.context['request'].user
        if user.role == 'business_admin':
            validated_data['scope'] = 'global'
        else:
            validated_data['store'] = user.store
            validated_data['scope'] = 'store'
        validated_data['tenant'] = user.tenant
        return super().create(validated_data)


class ProductVariantSerializer(serializers.ModelSerializer):
    current_price = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductVariant
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_current_price(self, obj):
        return obj.selling_price if obj.selling_price else obj.product.selling_price
    
    def get_is_in_stock(self, obj):
        return obj.quantity > 0


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    main_image_url = serializers.SerializerMethodField()
    additional_images_urls = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    profit_margin = serializers.SerializerMethodField()
    variant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'updated_at']
    
    def get_main_image_url(self, obj):
        if obj.main_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.main_image.url)
            return obj.main_image.url
        return None
    
    def get_additional_images_urls(self, obj):
        if obj.additional_images:
            request = self.context.get('request')
            urls = []
            for image_path in obj.additional_images:
                if request:
                    urls.append(request.build_absolute_uri(image_path))
                else:
                    urls.append(image_path)
            return urls
        return []
    
    def get_is_in_stock(self, obj):
        return obj.quantity > 0
    
    def get_is_low_stock(self, obj):
        return obj.quantity <= obj.min_quantity
    
    def get_current_price(self, obj):
        return obj.discount_price if obj.discount_price else obj.selling_price
    
    def get_profit_margin(self, obj):
        if obj.cost_price and obj.selling_price:
            return ((obj.selling_price - obj.cost_price) / obj.selling_price) * 100
        return 0
    
    def get_variant_count(self, obj):
        return obj.variants.count()
    
    def create(self, validated_data):
        user = self.context['request'].user
        if user.role == 'business_admin':
            validated_data['scope'] = 'global'
        else:
            validated_data['store'] = user.store
            validated_data['scope'] = 'store'
        validated_data['tenant'] = user.tenant
        
        # Handle file uploads
        main_image = self.context['request'].FILES.get('main_image')
        additional_images = self.context['request'].FILES.getlist('additional_images')
        
        if main_image:
            validated_data['main_image'] = main_image
        
        if additional_images:
            # Convert to list of file paths
            image_paths = []
            for image in additional_images:
                # Save the image and get the path
                image_paths.append(image.name)
            validated_data['additional_images'] = image_paths
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Handle file uploads
        main_image = self.context['request'].FILES.get('main_image')
        additional_images = self.context['request'].FILES.getlist('additional_images')
        
        if main_image:
            validated_data['main_image'] = main_image
        
        if additional_images:
            # Convert to list of file paths
            image_paths = []
            for image in additional_images:
                # Save the image and get the path
                image_paths.append(image.name)
            validated_data['additional_images'] = image_paths
        
        return super().update(instance, validated_data)


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    main_image_url = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    profit_margin = serializers.SerializerMethodField()
    variant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'description', 'category', 'category_name',
            'brand', 'cost_price', 'selling_price', 'discount_price',
            'quantity', 'min_quantity', 'max_quantity', 'weight',
            'dimensions', 'material', 'color', 'size', 'status',
            'is_featured', 'is_bestseller', 'main_image_url',
            'is_in_stock', 'is_low_stock', 'current_price',
            'profit_margin', 'variant_count', 'store', 'store_name',
            'scope', 'created_at', 'updated_at'
        ]
    
    def get_main_image_url(self, obj):
        if obj.main_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.main_image.url)
            return obj.main_image.url
        return None
    
    def get_is_in_stock(self, obj):
        return obj.quantity > 0
    
    def get_is_low_stock(self, obj):
        return obj.quantity <= obj.min_quantity
    
    def get_current_price(self, obj):
        return obj.discount_price if obj.discount_price else obj.selling_price
    
    def get_profit_margin(self, obj):
        if obj.cost_price and obj.selling_price:
            return ((obj.selling_price - obj.cost_price) / obj.selling_price) * 100
        return 0
    
    def get_variant_count(self, obj):
        return obj.variants.count()


class ProductDetailSerializer(ProductSerializer):
    class Meta(ProductSerializer.Meta):
        fields = list(ProductSerializer.Meta.fields) + ['additional_images_urls']


class ProductInventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    available_quantity = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    is_out_of_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductInventory
        fields = '__all__'
        read_only_fields = ['last_updated']
    
    def get_available_quantity(self, obj):
        return obj.available_quantity
    
    def get_is_low_stock(self, obj):
        return obj.is_low_stock
    
    def get_is_out_of_stock(self, obj):
        return obj.is_out_of_stock


class StockTransferSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    from_store_name = serializers.CharField(source='from_store.name', read_only=True)
    to_store_name = serializers.CharField(source='to_store.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = StockTransfer
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['requested_by'] = user
        return super().create(validated_data)


class StockTransferListSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    from_store_name = serializers.CharField(source='from_store.name', read_only=True)
    to_store_name = serializers.CharField(source='to_store.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = StockTransfer
        fields = [
            'id', 'from_store', 'from_store_name', 'to_store', 'to_store_name',
            'product', 'product_name', 'product_sku', 'quantity', 'reason',
            'requested_by', 'requested_by_name', 'approved_by', 'approved_by_name',
            'status', 'transfer_date', 'notes', 'created_at', 'updated_at'
        ]
