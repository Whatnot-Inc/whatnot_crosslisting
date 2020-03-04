import logging
import json
from datetime import datetime, timedelta
from aiotasks import build_manager

from app.utils import send_task
from app.db import CrossListingRepository, UserRepository
from app.models import CrossListing, User
from app.enums import CrossListingStates, MarketPlaces
from app.clients.whatnot.rest import WhatnotRestClient
from app.clients.ebay import EBayClient, TokenExpiredError
from .adaptors import SimpleEbayListingCreatorAdaptor
from .base import BaseService

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
            user.ebay_refresh_token = token['refresh_token']
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
        if cross_listing.status == CrossListingStates.SOLD.value:
            return cross_listing
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

    async def republish_older_than(self, days=30):

        wn_client = WhatnotRestClient()
        await wn_client.login(self.config['WHATNOT_USERNAME'], self.config['WHATNOT_PASSWORD'])
        data = await self.repository.get_active_in_the_last(days)
        print(data)
        for record in data:
            cross_listing = CrossListing.from_dict(record)
            print(f"Republishing listing {cross_listing.sku}")
            self.listing_data = await wn_client.get_listing_by_id(int(cross_listing.listing_id))
            self.product_data = await wn_client.get_product_by_id(int(self.listing_data['product_id']))
            event_data = {'price_cents': cross_listing.price_cents}
            if self.listing_data['status'] == 'active':
                await self.create(event_data)
            else:
                await self.deactivate(event_data)


    async def persist_crosslisting(self, listing_data, product_data, price_cents):
        price_cents = int(price_cents)
        cross_listing = await self.repository.get_by(sku=listing_data['uuid'])
        if cross_listing:
            cross_listing = dict(cross_listing)
            if cross_listing['price_cents'] != price_cents:
                cross_listing['price_cents'] = price_cents
                await self.repository.update({'id': cross_listing['id'],'price_cents': price_cents})
            return cross_listing
        crosslisting_dict = {
            'listing_id': listing_data['id'],
            'marketplace': self.marketplace.value,
            'price_cents': price_cents,
            'sku': listing_data['uuid'],
            'product_id': listing_data['product_id'],
            'product_upc': product_data.get('upc'),
            'product_name': product_data.get('name')
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
            print(self.listing_data)
            cross_listing = await self.repository.get_by(listing_id=int(self.listing_data['id']))
            print("got cross listing")
            print(cross_listing)
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

    async def suggest_category(self, q):
        mgmt = UserManager(db_conn=self.db_conn, config=self.config)
        user = await mgmt.get_or_create_default_user()
        user = await mgmt.update_ebay_token(user)

        ebay_client = EBayClient(self.config)
        await ebay_client.login(user)

        cat_tree = await ebay_client.get_default_category_tree_id()
        res = await ebay_client.get_category_suggestion(q, tree_id=cat_tree)
        return res

class OrderManager(BaseService):
    def __init__(self, user, secondary_external_id, **kwargs):
        super().__init__(**kwargs)
        self.user = user
        self.__secondary_id = secondary_external_id
        self.cross_listing = None


    async def setup(self):
        self.cross_listing = await self.repository.get_by(secondary_external_id=str(self.__secondary_id))
        self.cross_listing = CrossListing.from_dict(self.cross_listing)

    @property
    def repository(self):
        if not self._BaseService__repository:
            self._BaseService__repository = CrossListingRepository(self.db_conn)
        return super().repository

    async def pull_recent_orders(self, ebay_client, last_x_hours=5):
        since = datetime.now() - timedelta(hours=last_x_hours)
        response = await ebay_client.get_orders(since)
        for order in response['orders']:
            print('--------ORDER------------')
            print(order)
            print('--------XXXXX------------')
            for item in order['lineItems']:
                print(f"Evaluating {item['sku']}")
                record = await self.repository.get_by(sku=item['sku'])
                if not record:
                    print("No record found")
                    continue
                print(record)
                cross_listing = CrossListing.from_dict(record)
                if cross_listing.status != CrossListingStates.SOLD.value:
                    print("creating order")
                    self.cross_listing = cross_listing
                    await self.create_order({}, order_data=order)
                else:
                    print("Already processed")

    async def find_order(self, sku, ebay_client):
        if self.cross_listing is None:
            raise Exception('You forgot to setup the class, dude')
        since = datetime.now() - timedelta(days=5)
        response = await ebay_client.get_orders(since)
        for order in response['orders']:
            print('--------ORDER------------')
            print(order)
            print('--------XXXXX------------')
            for item in order['lineItems']:
                if item['sku'] == sku:
                    return order

    async def create_order(self, data, order_data=None):
        # TODO Should have an adapter here
        ebay_client = EBayClient(self.config)
        await ebay_client.login(self.user)

        wn_client = WhatnotRestClient()
        await wn_client.login(self.config['WHATNOT_USERNAME'], self.config['WHATNOT_PASSWORD'])

        listing_data = await wn_client.get_listing_by_id(int(self.cross_listing.listing_id))
        if order_data is None:
            order_data = await self.find_order(self.cross_listing.sku, ebay_client=ebay_client)
        address = {}
        for instruction in order_data['fulfillmentStartInstructions']:
            # if 'finalDestinationAddress' in instruction and instruction['finalDestinationAddress']:
            #     address = {**address, **instruction['finalDestinationAddress']}
            #     print(address)
            if 'shippingStep' in instruction and instruction['shippingStep']:
                step = instruction['shippingStep']
                if 'shipTo' in step:
                    address = {
                        'fullName': step['shipTo'].get('fullName', step['shipTo'].get('companyName', '')),
                        'phone': step['shipTo'].get('primaryPhone', {}).get('phoneNumber', None),
                        'email': step['shipTo'].get('email', 'ebay@whatnot.com'),
                        **address,
                        **step['shipTo']['contactAddress']
                    }
                    print(address)
                    break

        order_variables = {
            'email': address['email'],
            'full_name': address['fullName'],
            'address_line1': address['addressLine1'],
            'address_line2': address.get('addressLine2', ''),
            'address_city': address['city'],
            'address_state': address['stateOrProvince'],
            'address_postal_code': address['postalCode'],
            'address_country_code': address['countryCode'],
            'funding_source': json.dumps(order_data),
            'funding_source_display': 'ebay',
            'gateway': 'ebay',
            'shipping_method': 'ebay',
            'items': [
                {
                    'product_id': listing_data['product_id'],
                    'price_cents': self.cross_listing.price_cents,
                    'listing_id': self.cross_listing.listing_id
                }
            ]
        }
        print(order_variables)
        print("POSTING ORDER TO WHATNOT REST API !!")
        wn_order = await wn_client.create_order(order_variables)
        print(wn_order)

        self.cross_listing.status = CrossListingStates.SOLD.value
        await self.repository.update({'id': self.cross_listing.id, 'status': self.cross_listing.status})

        return wn_order

class LogisticManager(BaseService):
    def __init__(self, user, **kwargs):
        super().__init__(**kwargs)
        self.user = user

    @property
    def repository(self):
        if not self._BaseService__repository:
            self._BaseService__repository = CrossListingRepository(self.db_conn)
        return super().repository

    async def quote_outgoing(self, address_to, order, package_info=None):
        ebay_client = EBayClient(self.config)
        await ebay_client.login(self.user)

        package_info = package_info or {
            'width': 8,
            'height': 8,
            'length': 8,
            'weight': 9,
        }
        address_from = {
            'line1': self.config['WHATNOT_ADDRESS_LINE1'],
            'line2': self.config['WHATNOT_ADDRESS_LINE2'],
            'city': self.config['WHATNOT_ADDRESS_CITY'],
            'state': self.config['WHATNOT_ADDRESS_STATE'],
            'postal_code': self.config['WHATNOT_ADDRESS_ZIP'],
            'country':'US',
            'phone': '929 250 9523',
            'company_name': 'Whatnot Inc.'
        }

        orders = [ order ]

        res = await ebay_client.get_shipping_rates(package_info, address_from, address_to, orders)
        return res

    async def create_shipping_label(self, quote_id, rate_id):
        ebay_client = EBayClient(self.config)
        await ebay_client.login(self.user)

        res = await ebay_client.create_shipping_label(quote_id, rate_id)
        return res
