from django.db import models
from django.utils.translation import gettext_lazy as _


class Sale(models.Model):
    """
    Sales/Order model for tracking transactions.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        CONFIRMED = 'confirmed', _('Confirmed')
        PROCESSING = 'processing', _('Processing')
        SHIPPED = 'shipped', _('Shipped')
        DELIVERED = 'delivered', _('Delivered')
        CANCELLED = 'cancelled', _('Cancelled')
        REFUNDED = 'refunded', _('Refunded')

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PAID = 'paid', _('Paid')
        PARTIAL = 'partial', _('Partial')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')

    # Order Information
    order_number = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        related_name='sales'
    )
    
    # Sales Representative
    sales_representative = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='sales'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    # Financial Information
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Shipping Information
    shipping_address = models.TextField(blank=True, null=True)
    shipping_method = models.CharField(max_length=50, blank=True, null=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    
    # Tenant relationship
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='sales'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _('Sale')
        verbose_name_plural = _('Sales')
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} - {self.client.full_name}"

    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount

    @property
    def is_fully_paid(self):
        return self.paid_amount >= self.total_amount

    @property
    def is_delivered(self):
        return self.status == self.Status.DELIVERED

    def calculate_total(self):
        """Calculate the total amount including tax and discount."""
        total = self.subtotal + self.tax_amount - self.discount_amount + self.shipping_cost
        self.total_amount = total
        self.save()
        return total

    def mark_as_paid(self, amount=None):
        """Mark the sale as paid."""
        if amount:
            self.paid_amount += amount
        else:
            self.paid_amount = self.total_amount
        
        if self.paid_amount >= self.total_amount:
            self.payment_status = self.PaymentStatus.PAID
        elif self.paid_amount > 0:
            self.payment_status = self.PaymentStatus.PARTIAL
        
        self.save()


class SaleItem(models.Model):
    """
    Individual items in a sale.
    """
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='sale_items'
    )
    product_variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_items'
    )
    
    # Item details
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Discount
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Notes
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('Sale Item')
        verbose_name_plural = _('Sale Items')

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        """Calculate total price before saving."""
        self.total_price = (self.unit_price * self.quantity) - self.discount_amount
        super().save(*args, **kwargs)


class SalesPipeline(models.Model):
    """
    Sales pipeline for tracking leads and opportunities.
    """
    class Stage(models.TextChoices):
        LEAD = 'lead', _('Lead')
        CONTACTED = 'contacted', _('Contacted')
        QUALIFIED = 'qualified', _('Qualified')
        PROPOSAL = 'proposal', _('Proposal')
        NEGOTIATION = 'negotiation', _('Negotiation')
        CLOSED_WON = 'closed_won', _('Closed Won')
        CLOSED_LOST = 'closed_lost', _('Closed Lost')

    # Pipeline Information
    title = models.CharField(max_length=200)
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        related_name='pipelines'
    )
    sales_representative = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='pipelines'
    )
    
    # Stage and Progress
    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.LEAD
    )
    probability = models.PositiveIntegerField(
        default=0,
        help_text=_('Probability of closing (0-100%)')
    )
    
    # Financial Information
    expected_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Dates
    expected_close_date = models.DateField(blank=True, null=True)
    actual_close_date = models.DateField(blank=True, null=True)
    
    # Notes and Activities
    notes = models.TextField(blank=True, null=True)
    next_action = models.TextField(blank=True, null=True)
    next_action_date = models.DateTimeField(blank=True, null=True)
    
    # Tenant relationship
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='pipelines'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Sales Pipeline')
        verbose_name_plural = _('Sales Pipelines')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} - {self.client.full_name}"

    @property
    def is_closed(self):
        return self.stage in [self.Stage.CLOSED_WON, self.Stage.CLOSED_LOST]

    @property
    def is_won(self):
        return self.stage == self.Stage.CLOSED_WON

    def move_to_stage(self, new_stage):
        """Move the pipeline to a new stage."""
        self.stage = new_stage
        
        # Update probability based on stage
        stage_probabilities = {
            self.Stage.LEAD: 10,
            self.Stage.CONTACTED: 25,
            self.Stage.QUALIFIED: 50,
            self.Stage.PROPOSAL: 75,
            self.Stage.NEGOTIATION: 90,
            self.Stage.CLOSED_WON: 100,
            self.Stage.CLOSED_LOST: 0,
        }
        
        if new_stage in stage_probabilities:
            self.probability = stage_probabilities[new_stage]
        
        # Set close date if won or lost
        if new_stage in [self.Stage.CLOSED_WON, self.Stage.CLOSED_LOST]:
            from django.utils import timezone
            self.actual_close_date = timezone.now().date()
        
        self.save()
