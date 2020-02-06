import logging

from aiotasks import build_manager
from app.utils import send_task
from app.db import CrossListingRepository, UserRepository
from app.models import CrossListing, User
from app.enums import CrossListingStates, MarketPlaces
from .adaptors import SimpleEbayListingCreatorAdaptor
from .base import BaseService
from app.clients.whatnot.rest import WhatnotRestClient
from app.clients.ebay import EBayClient, TokenExpiredError
log = logging.getLogger(__name__)

class EventProcessor(BaseService):
    def __init__(self, event, **kwargs):
        super().__init__(**kwargs)
        self.event = event
        # self.task_manager = build_manager(dsn=f"redis://{self.config['REDIS_HOST']}:{self.config['REDIS_PORT']}/")

    async def process(self):
        if self.event.name == 'CreateListing':
            wn_client = WhatnotRestClient()
            await wn_client.login(self.config['WHATNOT_USERNAME'], self.config['WHATNOT_PASSWORD'])

            product_data = await wn_client.get_product_by_id(int(self.event.data['listing']['product_id']))
            print(product_data)
            log.info(f"Processing CreateList event for {self.event.data['listing']['id']}")
            return await self._process_create(self.event.data.pop('listing'), product_data)
        elif self.event.name == 'UpdateListing':
            return await self._process_update()
        elif self.event.name == 'DeactivateListing':
            return await self._process_deactivate(self.event.data.pop('listing'))
        else:
            raise Exception('Bad event')

    async def _process_create(self, listing_data, product_data):
        for marketplace in self.event.data['marketplaces']:
            creator = ListingManager(marketplace, listing_data, product_data, db_conn=self.db_conn, config=self.config)
            return await creator.create(self.event.data)
            # log.info(f"Creating task to process {self.event.data['listing_id']} at {marketplace}")
            # await send_task('create_marketplace_listing', args=(marketplace,), manager=self.task_manager, **self.event.data)

    async def _process_deactivate(self, listing_data):
        for marketplace in self.event.data['marketplaces']:
            manager = ListingManager(marketplace, listing_data, {}, db_conn=self.db_conn, config=self.config)
            return await manager.deactivate(self.event.data)

    async def _process_update(self):
        pass

class UserManager(BaseService):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = client = WhatnotRestClient()

    async def whatnot_login(self, email, password):
        await self.client.login(email, password)
        user = await self.repository.get_by(email=email)
        if user is None:
            user = {'email': email}
            user_entry = await self.repository.create(user)
        return True

    async def get_or_create_default_user(self):
        user_entry = await self.repository.first()
        if user_entry is None:
            user = {'email': 'seller@whatnot.com'}
            user_entry = await self.repository.create(user)

        return User.from_dict(user_entry)

    async def update_ebay_token(self, user, authorization_code=None):
        ebay_client = EBayClient(self.config)
        if authorization_code:
            token = await ebay_client.get_user_token(authorization_code)
            print(token)
            upd_data = {
                'id': user.id,
                'ebay_token': token['access_token'],
                'ebay_refresh_token': token['refresh_token']
            }
            user.ebay_token = token['access_token']
            user.ebay_refresh_token = token['ebay_refresh_token']
        else:
            token = await ebay_client.refresh_user_token(user.ebay_refresh_token)
            print(token)
            upd_data = {
                'id': user.id,
                'ebay_token': token['access_token']
            }
            user.ebay_token = token['access_token']
        await self.repository.update(upd_data)
        # TODO Schedule token refresh
        return user

    async def create_or_update_default_payment_policy(self, user, policy):
        ebay_client = EBayClient(self.config)
        await ebay_client.login(user)
        try:
            if user.ebay_payment_policy_id is None:
                res = await ebay_client.perform_request(ebay_client.client.create_payment_policy, body=policy)
                user.ebay_payment_policy_id = res['paymentPolicyId']
            else:
                res = await ebay_client.perform_request(ebay_client.client.update_payment_policy, policy, user.ebay_payment_policy_id)
                user.ebay_payment_policy_id = res['paymentPolicyId']
            await self.repository.update({'id': user.id, 'ebay_payment_policy_id': user.ebay_payment_policy_id})

            return res
        except TokenExpiredError:
            user = await self.update_ebay_token(user)
            return await self.create_or_update_default_payment_policy(user, policy)

    async def create_or_update_default_fulfillment_policy(self, user, policy):
        ebay_client = EBayClient(self.config)
        await ebay_client.login(user)
        try:
            if user.ebay_fulfillment_policy_id is None:
                res = await ebay_client.perform_request(ebay_client.client.create_fulfillment_policy, body=policy)
                user.ebay_fulfillment_policy_id = res['fulfillmentPolicyId']
            else:
                res = await ebay_client.perform_request(ebay_client.client.update_fulfillment_policy, policy, user.ebay_fulfillment_policy_id)
                user.ebay_fulfillment_policy_id = res['fulfillmentPolicyId']
            await self.repository.update({'id': user.id, 'ebay_fulfillment_policy_id': user.ebay_fulfillment_policy_id})

            return res
        except TokenExpiredError:
            user = await self.update_ebay_token(user)
            return await self.create_or_update_default_fulfillment_policy(user, policy)

    async def create_or_update_default_location(self, user, location, location_key):
        ebay_client = EBayClient(self.config)
        await ebay_client.login(user)
        try:
            if user.ebay_location_key != location_key:
                res = await ebay_client.perform_request(ebay_client.client.create_inventory_location, location, location_key)
                user.ebay_location_key = location_key
            else:
                res = await ebay_client.perform_request(ebay_client.client.update_inventory_location, location, user.ebay_location_key)
            await self.repository.update({'id': user.id, 'ebay_location_key': user.ebay_location_key})

            return res
        except TokenExpiredError:
            user = await self.update_ebay_token(user)
            return await self.create_or_update_default_location(user, policy)

    async def create_or_update_default_return_policy(self, user, policy):
        ebay_client = EBayClient(self.config)
        await ebay_client.login(user)
        try:
            if user.ebay_return_policy_id is None:
                res = await ebay_client.perform_request(ebay_client.client.create_return_policy, policy)
                user.ebay_return_policy_id = res['returnPolicyId']
            else:
                res = await ebay_client.perform_request(ebay_client.client.update_return_policy, policy, user.ebay_return_policy_id)
            await self.repository.update({'id': user.id, 'ebay_return_policy_id': user.ebay_return_policy_id})

            return res
        except TokenExpiredError:
            user = await self.update_ebay_token(user)
            return await self.create_or_update_default_return_policy(user, policy)

    @property
    def repository(self) -> UserRepository:
        if not self._BaseService__repository:
            self._BaseService__repository = UserRepository(self.db_conn)
        return super().repository


class ListingManager(BaseService):
    def __init__(self, marketplace, listing_data, product_data, **kwargs):
        super().__init__(**kwargs)
        self.__adaptor = kwargs.get('adaptor', None)
        self.listing_data = listing_data
        self.product_data = product_data
        self.marketplace = marketplace
        if type(self.marketplace) == str:
            self.marketplace = MarketPlaces(self.marketplace)

    @property
    def adaptor(self):
        if self.__adaptor is None:
            self.__adaptor = SimpleEbayListingCreatorAdaptor(self.config, self.repository)
        return self.__adaptor

    @property
    def repository(self):
        if not self._BaseService__repository:
            self._BaseService__repository = CrossListingRepository(self.db_conn)
        return super().repository

    async def create(self, event_data):
        cross_listing_entry = await self.persist_crosslisting(self.listing_data, self.product_data, event_data['price_cents'])
        # import pdb; pdb.set_trace()
        cross_listing = CrossListing.from_dict(cross_listing_entry)
        mgmt = UserManager(db_conn=self.db_conn, config=self.config)
        user = await mgmt.get_or_create_default_user()
        user = await mgmt.update_ebay_token(user)

        try:
            cross_listing = await self.adaptor.create_listing(self.listing_data, self.product_data, cross_listing, user)
        except TokenExpiredError:
            user = await mgmt.update_ebay_token(user)
            cross_listing = await self.adaptor.create_listing(self.listing_data, self.product_data, cross_listing, user)

        await self.repository.update(cross_listing.to_dict())
        return cross_listing


    async def persist_crosslisting(self, listing_data, product_data, price_cents):
        cross_listing = await self.repository.get_by(sku=listing_data['uuid'])
        if cross_listing:
            return cross_listing
        crosslisting_dict = {
            'listing_id': listing_data['id'],
            'marketplace': self.marketplace.value,
            'price_cents': int(price_cents),
            'sku': listing_data['uuid']
        }
        crosslisting_obj = CrossListing.from_dict(crosslisting_dict)
        crosslisting_obj.marketplace = self.marketplace.value
        crosslisting_obj.title = await self.adaptor.get_title(listing_data, product_data)
        crosslisting_obj.body = await self.adaptor.get_body(listing_data, product_data)
        crosslisting_obj.status = CrossListingStates.CREATED.value
        return await self.repository.create(crosslisting_obj)

    async def deactivate(self, event_data):
        mgmt = UserManager(db_conn=self.db_conn, config=self.config)
        user = await mgmt.get_or_create_default_user()
        user = await mgmt.update_ebay_token(user)

        try:
            print("getting cross listing")
            cross_listing = await self.repository.get_by(listing_id=self.listing_data['id'], marketplace=self.marketplace.value)
            print("got cross listing")
        except TokenExpiredError:
            user = await mgmt.update_ebay_token(user)
            cross_listing = await self.repository.get_by(listing_id=self.listing_data['id'], marketplace=self.marketplace.value)

        if cross_listing is None:
            raise Exception('Invalid Listing/Marketplace')

        cross_listing = CrossListing.from_dict(cross_listing)
        try:
            res = await self.adaptor.deactivate_listing(cross_listing, user)
        except TokenExpiredError:
            user = await mgmt.update_ebay_token(user)
            res = await self.adaptor.deactivate_listing(cross_listing, user)

        if res['listingId'] == cross_listing.secondary_external_id:
            cross_listing.status = CrossListingStates.DISABLED.value
            await self.repository.update({'id': cross_listing.id, 'status': cross_listing.status})

        return cross_listing
