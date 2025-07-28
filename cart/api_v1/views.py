from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from ..models import Cart, CartItem
from ..service import ProductService, UserService
from ..cart_manager import CartManager
from .serializers import (
    CartSerializer,
    AddToCartSerializer,
    CartSummarySerializer
)


class CartDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Cart.objects.prefetch_related('items')
    serializer_class = CartSerializer

    def get_object(self):
        """Get cart with validation for user/session ownership"""
        cart = super().get_object()
        
        # Check ownership
        user = self.request.user if self.request.user.is_authenticated else None
        session_key = self.request.session.session_key
        
        if user:
            if str(cart.user_id) != str(user.id):
                raise NotFound("Cart not found")
        else:
            if cart.session_key != session_key:
                raise NotFound("Cart not found")
        
        return cart

    def get_serializer_context(self):
        """Add services to serializer context"""
        context = super().get_serializer_context()
        context.update({
            'request': self.request,
            'product_service': ProductService,
            'user_service': UserService
        })
        return context

    def perform_destroy(self, instance):
        """Convert cart to abandoned status instead of deleting"""
        instance.status = 'abandoned'
        instance.save()


class AddToCartView(generics.CreateAPIView):
    serializer_class = AddToCartSerializer

    def get_cart(self):
        """Get or create cart using CartManager"""
        user = self.request.user if self.request.user.is_authenticated else None
        session_key = self.request.session.session_key
        
        if user:
            # Validate user exists in external service
            if not UserService.user_exists(user.id):
                raise ValidationError("User does not exist")
            return CartManager.get_user_cart(user.id)
        else:
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            return CartManager.get_session_cart(session_key)

    def create(self, request, *args, **kwargs):
        """Handle adding item to cart with product validation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart = self.get_cart()
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        
        # Validate product availability
        if not ProductService.validate_product_availability(product_id, quantity):
            raise ValidationError({
                'product_id': 'Product not available in requested quantity'
            })
        
        # Get product details
        product_data = ProductService.get_product(product_id)
        if not product_data:
            raise ValidationError({'product_id': 'Product not found'})
        
        # Create cart item
        item, created = CartItem.objects.update_or_create(
            cart=cart,
            product_id=product_id,
            defaults={
                'product_name': product_data['name'],
                'price_at_addition': product_data['price'],
                'quantity': quantity,
                'product_sku': product_data.get('sku', ''),
                'image_url': product_data.get('image_url', ''),
                'product_category': product_data.get('category', '')
            }
        )
        
        if not created:
            item.quantity += quantity
            item.save()
        
        # Return full cart state
        cart_serializer = CartSerializer(
            cart,
            context={
                'request': request,
                'product_service': ProductService,
                'user_service': UserService
            }
        )
        return Response(cart_serializer.data, status=status.HTTP_201_CREATED)


class CartListView(generics.ListAPIView):
    serializer_class = CartSummarySerializer

    def get_queryset(self):
        """Return carts for current user or session using CartManager"""
        user = self.request.user if self.request.user.is_authenticated else None
        session_key = self.request.session.session_key
        
        if user:
            if not UserService.user_exists(user.id):
                return Cart.objects.none()
            return Cart.objects.filter(user_id=user.id)
        elif session_key:
            return Cart.objects.filter(session_key=session_key)
        return Cart.objects.none()


class MergeCartsView(generics.GenericAPIView):
    """View for merging session cart with user cart after login"""
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise ValidationError("User must be authenticated")
        
        session_key = request.session.session_key
        if not session_key:
            return Response({'detail': 'No session cart to merge'})
        
        # Get both carts
        try:
            user_cart = CartManager.get_user_cart(request.user.id)
            session_cart = Cart.objects.get(
                session_key=session_key,
                status='active'
            )
        except Cart.DoesNotExist:
            return Response({'detail': 'No session cart to merge'})
        
        # Merge carts
        CartManager.merge_carts(user_cart, session_cart)
        
        # Return merged cart
        serializer = CartSerializer(
            user_cart,
            context={
                'request': request,
                'product_service': ProductService,
                'user_service': UserService
            }
        )
        return Response(serializer.data)