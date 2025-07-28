import requests
from requests.exceptions import RequestException, Timeout
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential
from django.conf import settings

class BaseService:
    API_TIMEOUT = 3  # seconds
    MAX_RETRIES = 3
    
    @classmethod
    def _make_request(cls, url):
        try:
            response = requests.get(
                url,
                timeout=cls.API_TIMEOUT
            )
            response.raise_for_status()  # Raises HTTPError for bad responses
            return response
        except Timeout:
            print(f"Request to {url} timed out")
            return None
        except RequestException as e:
            print(f"Error making request to {url}: {str(e)}")
            return None

class ProductService(BaseService):
    BASE_URL = getattr(settings, 'PRODUCT_SERVICE_URL', 'http://localhost:7000')
    
    @staticmethod
    @retry(stop=stop_after_attempt(BaseService.MAX_RETRIES),
          wait=wait_exponential(multiplier=1, min=2, max=10))
    @lru_cache(maxsize=128)
    def get_product(product_id):
        url = f"{ProductService.BASE_URL}/product/{product_id}"
        response = ProductService._make_request(url)
        return response.json() if response else None

    @staticmethod
    def validate_product_availability(product_id, quantity):
        product = ProductService.get_product(product_id)
        return product and product.get('stock', 0) >= quantity

class UserService(BaseService):
    BASE_URL = getattr(settings, 'USER_SERVICE_URL', 'https://user-service/api')
    
    @staticmethod
    @retry(stop=stop_after_attempt(BaseService.MAX_RETRIES),
          wait=wait_exponential(multiplier=1, min=2, max=10))
    def user_exists(user_id):
        url = f"{UserService.BASE_URL}/users/{user_id}/exists"
        response = UserService._make_request(url)
        return response is not None and response.status_code == 200