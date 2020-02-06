import tempfile
import base64
from urllib.parse import urlencode

import asyncio
import aiohttp
from app.clients.base.rest import BaseRestClient, RestResponseError
from app.settings import load_config
config = load_config()

class EbayRestClient(BaseRestClient):
    def login(self):
        auth_header_data = config['EBAY_CLIENT_ID'] + ':' + config['EBAY_CLIENT_SECRET']
        self.basic_auth = base64.b64encode(str.encode(auth_header_data)).decode('utf-8')

    async def get_user_token(self, authorization_code):
        self.login()
        headers = {
            "Content-Type" : "application/x-www-form-urlencoded",
        }

        body= {
            "grant_type" : "authorization_code",
            "code": authorization_code,
            "redirect_uri" : config['EBAY_RU_NAME'],
        }

        token_url = f"{config['EBAY_API_BASE_URL']}/identity/v1/oauth2/token"

        print(token_url)
        print({**self.default_headers, **headers})
        print(body)

        async with aiohttp.ClientSession() as client:
            try:
                async with client.post(token_url, data=body, headers={**self.default_headers, **headers}) as resp:
                    print(resp.status)
                    return await resp.json()
            except aiohttp.ClientPayloadError as ex:
                print(f'Client PayloadError {ex.status}. Message: {ex.message}', ex)
                raise ex
            except aiohttp.ClientError as ex:
                print('ClientError',ex)
                raise ex

    async def refresh_user_token(self, refresh_token):
        # Gets cached token or generate a new one
        self.login()

        headers = {
            "Content-Type" : "application/x-www-form-urlencoded",
        }

        body= {
            "grant_type" : "refresh_token",
            "refresh_token": refresh_token,
            "scope" : 'https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/buy.order.readonly https://api.ebay.com/oauth/api_scope/buy.guest.order https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.analytics.readonly https://api.ebay.com/oauth/api_scope/sell.marketplace.insights.readonly https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly https://api.ebay.com/oauth/api_scope/buy.shopping.cart https://api.ebay.com/oauth/api_scope/buy.offer.auction https://api.ebay.com/oauth/api_scope/commerce.identity.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.email.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.phone.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.address.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.name.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.status.readonly https://api.ebay.com/oauth/api_scope/sell.finances https://api.ebay.com/oauth/api_scope/sell.item.draft https://api.ebay.com/oauth/api_scope/sell.payment.dispute https://api.ebay.com/oauth/api_scope/sell.item',
        }

        token_url = f"{config['EBAY_API_BASE_URL']}/identity/v1/oauth2/token"

        async with aiohttp.ClientSession() as client:
            try:
                async with client.post(token_url, data=body, headers={**self.default_headers, **headers}) as resp:
                    print(resp.status)
                    return await resp.json()
            except aiohttp.ClientPayloadError as ex:
                print(f'Client PayloadError {ex.status}. Message: {ex.message}', ex)
                raise ex
            except aiohttp.ClientError as ex:
                print('ClientError',ex)
                raise ex

    async def create_inventory_location(self, body, location_key):
        response_data = await self._post(config['EBAY_API_BASE_URL'] + "/sell/inventory/v1/location/" + location_key, body=body)
        print(response_data)
        return response_data

    async def update_inventory_location(self, body, location_key):
        response_data = await self._post(config['EBAY_API_BASE_URL'] + "/sell/inventory/v1/location/" + location_key + '/update_location_details', body=body)
        print(response_data)
        return response_data

    async def create_or_replace_inventory_item(self, body, sku):
        response_data = await self._put(config['EBAY_API_BASE_URL'] + "/sell/inventory/v1/inventory_item/" + sku, body=body)
        return response_data

    async def create_offer(self, body):
        response_data = await self._post(config['EBAY_API_BASE_URL'] + "/sell/inventory/v1/offer", body=body)
        return response_data

    async def get_offers(self, sku):
        url = config['EBAY_API_BASE_URL'] + "/sell/inventory/v1/offer/?"
        url += urlencode({'sku': sku})
        response_data = await self._get(url)
        return response_data

    async def update_offer(self, offer_id, body):
        response_data = await self._put(config['EBAY_API_BASE_URL'] + "/sell/inventory/v1/offer/" + offer_id , body=body)
        return response_data

    async def publish_offer(self, offer_id):
        response_data = await self._post(config['EBAY_API_BASE_URL'] + "/sell/inventory/v1/offer/" + offer_id + "/publish")
        return response_data

    async def withdraw_offer(self, offer_id):
        response_data = await self._post(config['EBAY_API_BASE_URL'] + "/sell/inventory/v1/offer/" + offer_id + "/withdraw")
        return response_data

    async def get_default_category_tree_id(self, marketplace_id):
        url = config['EBAY_API_BASE_URL'] + "/commerce/taxonomy/v1_beta/get_default_category_tree_id?"
        url += urlencode({'marketplace_id': marketplace_id})
        response_data = await self._get(url)
        return response_data

    async def get_category_tree(self, category_tree_id):
        url = config['EBAY_API_BASE_URL'] + f"/commerce/taxonomy/v1_beta/category_tree/{category_tree_id}"
        response_data = await self._get(url)

    async def get_category_suggestions(self, tree_id, q):
        url = config['EBAY_API_BASE_URL'] + "/commerce/taxonomy/v1_beta/category_tree/" + tree_id + "/get_category_suggestions?"
        url += urlencode({'q': q})

        response_data = await self._get(url)
        return response_data

    async def get_payment_policies(self, marketplace):
        url = config['EBAY_API_BASE_URL'] + "/sell/account/v1/payment_policy?"
        url += urlencode({'marketplace_id': marketplace})

        response_data = await self._get(url)
        return response_data

    async def create_payment_policy(self, body):
        url = config['EBAY_API_BASE_URL'] + "/sell/account/v1/payment_policy"
        response_data = await self._post(url, body)
        return response_data

    async def update_payment_policy(self, body, policy_id):
        url = config['EBAY_API_BASE_URL'] + "/sell/account/v1/payment_policy/" + policy_id
        response_data = await self._put(url, body)
        return response_data

    async def get_return_policy(self, marketplace):
        url = config['EBAY_API_BASE_URL'] + "/sell/account/v1/return_policy?"
        url += urlencode({'marketplace_id': marketplace})

        response_data = await self._get(url)
        return response_data

    async def create_return_policy(self, body):
        url = config['EBAY_API_BASE_URL'] + "/sell/account/v1/return_policy"
        response_data = await self._post(url, body)
        return response_data

    async def update_return_policy(self, body, policy_id):
        url = config['EBAY_API_BASE_URL'] + "/sell/account/v1/return_policy/" + policy_id
        response_data = await self._put(url, body)
        return response_data

    async def get_fulfillment_policies(self, marketplace):
        url = config['EBAY_API_BASE_URL'] + "/sell/account/v1/fulfillment_policy?"
        url += urlencode({'marketplace_id': marketplace})

        response_data = await self._get(url)
        return response_data

    async def create_fulfillment_policy(self, body):
        url = config['EBAY_API_BASE_URL'] + "/sell/account/v1/fulfillment_policy"
        response_data = await self._post(url, body)
        return response_data

    async def update_fulfillment_policy(self, body, policy_id):
        url = config['EBAY_API_BASE_URL'] + "/sell/account/v1/fulfillment_policy/" + policy_id
        response_data = await self._put(url, body)
        return response_data

    async def get_rate_tables(self, country_code):
        url = config['EBAY_API_BASE_URL'] + "/sell/account/v1/rate_table?"
        url += urlencode({'country_code': country_code})
