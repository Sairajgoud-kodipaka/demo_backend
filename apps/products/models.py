from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class Category(models.Model):
    """
    Product category model.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    
    # Tenant relationship
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='categories'
    )
    
    # Store relationship for store-specific categories
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='categories'
    )
    
    # Scope: global (business admin) or store (store manager)
    SCOPE_CHOICES = [
        ('global', 'Global'),
        ('store', 'Store')
    ]
    scope = models.CharField(
        max_length=10,
        choices=SCOPE_CHOICES,
        default='store',
        help_text=_('Global categories are visible to all stores, Store categories are store-specific')
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['name']
        unique_together = ['name', 'tenant', 'store']

    def __str__(self):
        store_info = f" ({self.store.name})" if self.store else ""
        return f"{self.name}{store_info}"

    @property
    def full_name(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Product(models.Model):
    """
    Product model for inventory management.
    """
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        DISCONTINUED = 'discontinued', _('Discontinued')
        OUT_OF_STOCK = 'out_of_stock', _('Out of Stock')

    # Basic Information
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, help_text=_('Stock Keeping Unit'))
    description = models.TextField(blank=True, null=True)
    
    # Category and Brand
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    brand = models.CharField(max_length=100, blank=True, null=True)
    
    # Pricing
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, help_text=_('Cost price'))
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, help_text=_('Selling price'))
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Inventory (keeping for backward compatibility, will be replaced by ProductInventory)
    quantity = models.PositiveIntegerField(default=0)
    min_quantity = models.PositiveIntegerField(default=0, help_text=_('Minimum stock level'))
    max_quantity = models.PositiveIntegerField(default=1000, help_text=_('Maximum stock level'))
    
    # Product Details
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text=_('Weight in grams'))
    dimensions = models.CharField(max_length=100, blank=True, null=True, help_text=_('Dimensions: LxWxH'))
    material = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=20, blank=True, null=True)
    
    # Status and Visibility
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    
    # Images
    main_image = models.ImageField(upload_to='products/', blank=True, null=True)
    additional_images = models.JSONField(default=list, blank=True)
    
    # SEO and Marketing
    meta_title = models.CharField(max_length=200, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    
    # Tenant relationship
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='products'
    )
    
    # Store relationship for store-specific products
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='products'
    )
    
    # Scope: global (business admin) or store (store manager)
    SCOPE_CHOICES = [
        ('global', 'Global'),
        ('store', 'Store')
    ]
    scope = models.CharField(
        max_length=10,
        choices=SCOPE_CHOICES,
        default='store',
        help_text=_('Global products are visible to all stores, Store products are store-specific')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['-created_at']
        unique_together = ['sku', 'tenant', 'store']

    def __str__(self):
        store_info = f" ({self.store.name})" if self.store else ""
        return f"{self.name} ({self.sku}){store_info}"

    @property
    def is_in_stock(self):
        return self.quantity > 0 and self.status == self.Status.ACTIVE

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_quantity

    @property
    def current_price(self):
        return self.discount_price if self.discount_price else self.selling_price

    @property
    def profit_margin(self):
        if self.cost_price and self.current_price:
            return ((self.current_price - self.cost_price) / self.current_price) * 100
        return 0

    def update_stock(self, quantity_change, operation='add'):
        """Update product stock quantity."""
        if operation == 'add':
            self.quantity += quantity_change
        elif operation == 'subtract':
            self.quantity = max(0, self.quantity - quantity_change)
        
        # Update status based on quantity
        if self.quantity == 0:
            self.status = self.Status.OUT_OF_STOCK
        elif self.status == self.Status.OUT_OF_STOCK and self.quantity > 0:
            self.status = self.Status.ACTIVE
        
        self.save()


class ProductInventory(models.Model):
    """
    Store-specific inventory tracking for products.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory'
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='inventory'
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0, help_text=_('Items reserved for pending orders'))
    reorder_point = models.PositiveIntegerField(default=0, help_text=_('Stock level at which to reorder'))
    max_stock = models.PositiveIntegerField(default=1000, help_text=_('Maximum stock level'))
    location = models.CharField(max_length=100, blank=True, null=True, help_text=_('Specific location within store'))
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Product Inventory')
        verbose_name_plural = _('Product Inventories')
        unique_together = ('product', 'store')
        ordering = ['-last_updated']

    def __str__(self):
        return f"{self.product.name} - {self.store.name} ({self.quantity})"

    @property
    def available_quantity(self):
        """Available quantity (total - reserved)"""
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_low_stock(self):
        """Check if stock is below reorder point"""
        return self.quantity <= self.reorder_point

    @property
    def is_out_of_stock(self):
        """Check if product is out of stock"""
        return self.quantity == 0


class StockTransfer(models.Model):
    """
    Inter-store stock transfer model.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]

    from_store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='outgoing_transfers'
    )
    to_store = models.ForeignKey(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='incoming_transfers'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='transfers'
    )
    quantity = models.PositiveIntegerField()
    reason = models.TextField(help_text=_('Reason for transfer'))
    requested_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='transfer_requests'
    )
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='transfer_approvals',
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    transfer_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Stock Transfer')
        verbose_name_plural = _('Stock Transfers')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.from_store.name} to {self.to_store.name} ({self.quantity})"

    def approve(self, approved_by_user):
        """Approve the transfer"""
        self.status = 'approved'
        self.approved_by = approved_by_user
        self.save()

    def complete(self):
        """Complete the transfer"""
        # Update inventory
        from_inventory, created = ProductInventory.objects.get_or_create(
            product=self.product,
            store=self.from_store,
            defaults={'quantity': 0}
        )
        to_inventory, created = ProductInventory.objects.get_or_create(
            product=self.product,
            store=self.to_store,
            defaults={'quantity': 0}
        )

        # Transfer the stock
        if from_inventory.quantity >= self.quantity:
            from_inventory.quantity -= self.quantity
            to_inventory.quantity += self.quantity
            from_inventory.save()
            to_inventory.save()
            
            self.status = 'completed'
            self.transfer_date = timezone.now()
            self.save()
            return True
        else:
            return False

    def cancel(self):
        """Cancel the transfer"""
        self.status = 'cancelled'
        self.save()


class ProductVariant(models.Model):
    """
    Product variant model for products with multiple options (size, color, etc.).
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    
    # Variant attributes
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, help_text=_('Variant name, e.g., "Red, Large"'))
    
    # Attributes
    attributes = models.JSONField(default=dict, help_text=_('Variant attributes like color, size, etc.'))
    
    # Pricing and inventory
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Product Variant')
        verbose_name_plural = _('Product Variants')
        unique_together = ['product', 'sku']

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def current_price(self):
        return self.product.current_price + self.price_adjustment

    @property
    def is_in_stock(self):
        return self.quantity > 0 and self.is_active
