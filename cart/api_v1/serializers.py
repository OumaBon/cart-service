from rest_framework import serializers
from ..models import Cart, CartItem
from decimal import Decimal
import uuid


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField()
    total_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            'id',
            'product_id',
            'product_name',
            'product_sku',
            'price_at_addition',
            'quantity',
            'total_price',
            'image_url',
            'product_category',
            'added_at'
        ]
        read_only_fields = [
            'id',
            'product_name',
            'product_sku',
            'price_at_addition',
            'total_price',
            'image_url',
            'product_category',
            'added_at'
        ]

    def validate_product_id(self, value):
        """Validate product_id exists in external service"""
        # In a real implementation, you would call your product service here
        if not self.context.get('skip_product_validation', False):
            # Example pseudo-code:
            # if not product_service.exists(value):
            #     raise serializers.ValidationError("Product does not exist")
            pass
        return value

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, required=False)
    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id',
            'user_id',
            'session_key',
            'status',
            'items',
            'subtotal',
            'total',
            'item_count',
            'shipping_cost',
            'discount_amount',
            'tax_amount',
            'currency_code',
            'coupon_code',
            'discount_notes',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'status',
            'subtotal',
            'total',
            'item_count',
            'created_at',
            'updated_at'
        ]

    def validate_user_id(self, value):
        """Validate user_id exists in external service"""
        if value and not self.context.get('skip_user_validation', False):
            # Example pseudo-code:
            # if not user_service.exists(value):
            #     raise serializers.ValidationError("User does not exist")
            pass
        return value

    def validate(self, data):
        """Ensure either user_id or session_key is provided"""
        if not data.get('user_id') and not data.get('session_key'):
            raise serializers.ValidationError(
                "Either user_id or session_key must be provided"
            )
        return data

    def create(self, validated_data):
        """Handle cart creation with nested items"""
        items_data = validated_data.pop('items', [])
        cart = Cart.objects.create(**validated_data)
        
        for item_data in items_data:
            CartItem.objects.create(cart=cart, **item_data)
        
        return cart

    def update(self, instance, validated_data):
        """Handle cart updates with nested items"""
        items_data = validated_data.pop('items', None)
        
        # Update cart fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Handle items update if provided
        if items_data is not None:
            self.update_cart_items(instance, items_data)
        
        return instance

    def update_cart_items(self, cart, items_data):
        """Update cart items while maintaining data consistency"""
        current_items = {str(item.product_id): item for item in cart.items.all()}
        updated_product_ids = set()
        
        # Update or create items
        for item_data in items_data:
            product_id = str(item_data['product_id'])
            if product_id in current_items:
                # Update existing item
                item = current_items[product_id]
                for key, value in item_data.items():
                    setattr(item, key, value)
                item.save()
            else:
                # Create new item
                CartItem.objects.create(cart=cart, **item_data)
            updated_product_ids.add(product_id)
        
        # Remove items not in the update
        for product_id, item in current_items.items():
            if product_id not in updated_product_ids:
                item.delete()


class AddToCartSerializer(serializers.Serializer):
    """
    Specialized serializer for adding items to cart
    with product validation from external service
    """
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(
        min_value=1,
        default=1
    )

    def validate(self, data):
        """Validate product exists and get current details"""
        product_id = data['product_id']
        
        # In a real implementation, call your product service here
        # product_data = product_service.get(product_id)
        # if not product_data:
        #     raise serializers.ValidationError("Product not found")
        
        # Mock response for example purposes
        product_data = {
            'id': product_id,
            'name': "Example Product",
            'price': "19.99",
            'sku': "PROD-001",
            'image_url': "https://example.com/product.jpg",
            'category': "Example Category"
        }
        
        data['product_details'] = product_data
        return data

    def create(self, validated_data):
        """Create cart item with product details"""
        cart = self.context['cart']
        product_data = validated_data['product_details']
        
        item, created = CartItem.objects.update_or_create(
            cart=cart,
            product_id=validated_data['product_id'],
            defaults={
                'product_name': product_data['name'],
                'price_at_addition': Decimal(product_data['price']),
                'quantity': validated_data['quantity'],
                'product_sku': product_data.get('sku', ''),
                'image_url': product_data.get('image_url', ''),
                'product_category': product_data.get('category', '')
            }
        )
        
        if not created:
            item.quantity += validated_data['quantity']
            item.save()
        
        return item


class CartSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for cart summaries in lists
    """
    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id',
            'user_id',
            'status',
            'subtotal',
            'item_count',
            'currency_code',
            'updated_at'
        ]