from app.clients.base.rest import BaseRestClient
from app.settings import load_config
config = load_config()

class WhatnotRestClient(BaseRestClient):
    def __init__(self, cache=None, bearer_token=None, basic_auth=None):
        super().__init__(cache=cache, bearer_token=bearer_token, basic_auth=basic_auth)

    async def login(self, email, pwd):
        token = await self._get_token(email, pwd)
        self.bearer_token = token
        return True

    async def _get_token(self, username, password):
        response_data = await self._post(f"{config['WHATNOT_API_BASE_URL']}/private/api/login", {
            "username": username,
            "password": password
        })
        print(response_data)
        return response_data['access_token']

    async def login_user(self, username, password):
        token = self._get_token(email, pwd)
        return token

    async def get_product_by_id(self, product_id):
        response_data = await self._get(f"{config['WHATNOT_API_BASE_URL']}/private/api/products/{product_id}")
        return response_data

    async def get_listing_by_id(self, listing_id):
        return await self._get(f"{config['WHATNOT_API_BASE_URL']}/private/api/listings/{listing_id}")

    async def create_order(self, data):
        return await self._post(f"{config['WHATNOT_API_BASE_URL']}/private/api/orders", body=data)

