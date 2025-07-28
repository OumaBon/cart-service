from .models import Cart, CartItem


class CartManager:
    """
    Handles cart-related database operations
    """
    
    @staticmethod
    def get_user_cart(user_id):
        cart, created = Cart.objects.get_or_create(
            user_id=user_id,
            status='active',
            defaults={'session_key': None}
        )
        return cart

    @staticmethod
    def get_session_cart(session_key):
        cart, created = Cart.objects.get_or_create(
            session_key=session_key,
            user_id=None,
            status='active'
        )
        return cart

    @staticmethod
    def merge_carts(user_cart, session_cart):
        for item in session_cart.items.all():
            try:
                user_item = user_cart.items.get(product_id=item.product_id)
                user_item.quantity += item.quantity
                user_item.save()
            except CartItem.DoesNotExist:
                item.cart = user_cart
                item.save()
        session_cart.delete()