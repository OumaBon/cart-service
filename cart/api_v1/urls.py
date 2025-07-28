from django.urls import path
from .views import (
    CartDetailView,
    AddToCartView,
    CartListView,
    MergeCartsView
)


app_name = 'api_v1'  

urlpatterns = [
    # Cart collection endpoints
    path('carts/', CartListView.as_view(), name='cart-list'),
    path('carts/add/', AddToCartView.as_view(), name='add-to-cart'),
    path('carts/merge/', MergeCartsView.as_view(), name='merge-carts'),
    
    # Cart instance endpoints
    path('carts/<uuid:pk>/', CartDetailView.as_view(), name='cart-detail'),
]