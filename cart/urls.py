from django.urls import path, include
from cart.api_v1 import urls as api_v1_urls


urlpatterns = [
    path('', include('cart.api_v1.urls')),
    # Future versions would go here:
    # path('api/v2/', include('cart.api_v2.urls', namespace='v2')),
]