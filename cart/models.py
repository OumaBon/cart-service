import uuid
from django.db import models
from django.core.validators import MinValueValidator



class Cart(models.Model):
    CART_STATUS = (
        ('active', 'Active'),
        ('abandoned', 'Abandoned'),
        ('converted', 'Converted to Order'),
        ('merged', 'Merged with another cart'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Reference to external user service (not a ForeignKey)
    user_id = models.UUIDField(null=True, blank=True)
    
    # For anonymous users
    session_key = models.CharField(max_length=40, null=True, blank=True)
    
    # Cart metadata
    status = models.CharField(
        max_length=20,
        choices=CART_STATUS,
        default='active'
    )
    
    # Pricing fields (all values in currency base units)
    shipping_cost = models.DecimalField(
        max_digits=12,  # Increased for high-value items
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    
    # Currency information
    currency_code = models.CharField(max_length=3, default='USD')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Promotional metadata
    coupon_code = models.CharField(max_length=20, null=True, blank=True)
    discount_notes = models.TextField(null=True, blank=True)
    
    class Meta:
        unique_together = [('user_id', 'status')] if 'user_id' else []
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['session_key']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        identifier = f"User:{self.user_id}" if self.user_id else f"Session:{self.session_key}"
        return f"Cart {self.id} ({identifier}) [{self.status}]"
    
    @property
    def is_anonymous(self):
        return self.user_id is None
    
    @property
    def subtotal(self):
        """Sum of all cart items before adjustments"""
        return sum(item.total_price for item in self.items.all())
    
    @property
    def total(self):
        """Final total including all adjustments"""
        total = self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount
        return max(0, total)  # Ensure never negative
    
    @property
    def item_count(self):
        """Total quantity of items in cart"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    def clear(self):
        """Remove all items from cart"""
        self.items.all().delete()
        self.refresh_pricing()
    
    def refresh_pricing(self):
        """Recalculate all pricing fields (would call external services)"""
        # Placeholder for actual implementation
        self.shipping_cost = 0  # Would call shipping service
        self.tax_amount = 0     # Would call tax service
        self.save()
    
    def convert_to_order(self, order_service_client):
        """Convert cart to order in external order service"""
        order_data = {
            'cart_id': str(self.id),
            'user_id': str(self.user_id) if self.user_id else None,
            'items': [
                {
                    'product_id': str(item.product_id),
                    'quantity': item.quantity,
                    'unit_price': float(item.price_at_addition),
                    'currency': self.currency_code
                }
                for item in self.items.all()
            ],
            'totals': {
                'subtotal': float(self.subtotal),
                'shipping': float(self.shipping_cost),
                'tax': float(self.tax_amount),
                'discount': float(self.discount_amount),
                'total': float(self.total)
            }
        }
        
        # Call external order service
        response = order_service_client.create_order(order_data)
        if response.success:
            self.status = 'converted'
            self.save()
            return True
        return False


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(
        Cart,
        related_name='items',
        on_delete=models.CASCADE
    )
    
    # Reference to external product service
    product_id = models.UUIDField()
    
    # Product details snapshot
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=50, null=True, blank=True)
    price_at_addition = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    
    # Product metadata
    image_url = models.URLField(null=True, blank=True)
    product_category = models.CharField(max_length=100, null=True, blank=True)
    
    # Timestamps
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [('cart', 'product_id')]
        ordering = ['-added_at']
        indexes = [
            models.Index(fields=['product_id']),
        ]
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name} ({self.product_id})"
    
    @property
    def total_price(self):
        return self.quantity * self.price_at_addition
    
    def update_quantity(self, new_quantity):
        """Update quantity with validation"""
        if new_quantity < 1:
            raise ValueError("Quantity must be at least 1")
        self.quantity = new_quantity
        self.save()
        self.cart.refresh_pricing()