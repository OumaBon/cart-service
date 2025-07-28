import requests

class ProductService:
    @staticmethod
    def get_product(product_id):
        response = requests.get(f'https://product-service/api/products/{product_id}')
        if response.status_code == 200:
            return response.json()
        return None

    @staticmethod
    def validate_product_availability(product_id, quantity):
        product = ProductService.get_product(product_id)
        if not product:
            return False
        return product['stock'] >= quantity



class UserService:
    @staticmethod
    def user_exists(user_id):
        response = requests.get(f'https://user-service/api/users/{user_id}/exists')
        return response.status_code == 200