from ebaysdk.trading import Connection as Trading
from app.settings import load_config
from .rest import EbayRestClient, RestResponseError, get_scopes
config = load_config()


def get_ebay_conscent_link(client_id, redirect_uri):
    return f"{config['EBAY_API_AUTH_BASE_URL']}/oauth2/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={get_scopes()}"

class TokenExpiredError(Exception):
    pass

class EBayClient:
    def __init__(self, config):
        self.__api_instance = None
        self.config = config
        self.client = EbayRestClient()
        self.soap_api = None

    async def login(self, user):
        self.client.oauth_login(user.ebay_token)
        self.soap_api = Trading(
            appid=config['CREDS_APPID'],
            devid=config['CREDS_DEVID'],
            certid=config['CREDS_CERTID'],
            token=user.ebay_token,
            config_file=None
        )

    async def get_user_token(self, code):
        return await self.client.get_user_token(code)

    async def refresh_user_token(self, ebay_refresh_token):
        return await self.client.refresh_user_token(ebay_refresh_token)

    def is_token_expired(self, response_data):
        if response_data and 'errors' in response_data and len(response_data['errors']):
            if response_data['errors'][0]['errorId'] == 1001 and response_data['errors'][0]['domain'] == 'OAuth':
                return True
        return False

    async def perform_request(self, method, *args, **kwargs):
        try:
            result = await method(*args, **kwargs)
            return result
        except RestResponseError as rre:
            if self.is_token_expired(rre.json) or rre.status_code == 401:
                raise TokenExpiredError
            raise rre
        except Exception as ex:
            print(ex)
            import traceback
            traceback.print_exc()
            raise ex

    def add_item(self, product_data, listing_data, cross_listing):
        cond = 'NEW'
        item = dict(
            ConditionDescription=f"Item is in {listing_data['condition_name']} conditions and authenticated by a specialist",
            ConditionID=cond,
            Country='US',
            Currency='USD',
            Description=cross_listing.body,
            DispatchTimeMax=10,
            ItemSpecifics=[
                {"Name": "Brand", "Value": "Funko"},
                {"Name": "Franchise", "Value": "Pop"},
                {"Name": "Exclusivity", "Value": product_data['product_profile'].get('exclusive', 'N/A')},
                {"Name": "Box Number", "Value": product_data['product_profile'].get('box_number', 'N/A') or 'N/A'},
                {"Name": "License", "Value": product_data['product_profile'].get('license', 'N/A')},
            ],
            ListingType="FixedPriceItem",
            PrimaryCategory={"CategoryID": config['EBAY_CATEGORY_ID']},
            ProductListingDetails=dict(
                BrandMPN=dict(
                    Brand='Funko',
                    MPN=product_data['item_number'] or (product_data['product_profile'].get('item_number', 'N/A') or 'N/A')
                ),
                UPC=product_data['upc']
            ),
            PictureDetails=[ dict(PictureURL=image['public_url']) for image in images],

            Quantity=1,
            ShippingDetails=dict(
                CalculatedShippingRate=dict(
                    OriginatingPostalCode=config['WHATNOT_ADDRESS_ZIP'],
                    PackagingHandlingCosts={
                        '#text': 2.50,
                        '@attrs': dict(currencyID='USD')
                    },
                ),
            ),
            ShippingPackageDetails=dict(
                MeasurementUnit='English',
                PackageDepth={
                    '#text': 9.0,
                    '@attrs': dict(unit='in')
                },
                PackageLength={
                    '#text': 9.0,
                    '@attrs': dict(unit='in')
                },
                PackageWidth={
                    '#text': 9.0,
                    '@attrs': dict(unit='in')
                },
                ShippingPackage='MAILING_BOX',
                WeightMajor={
                    '#text': 12.0,
                    '@attrs': dict(unit='oz')
                },
                WeightMinor={
                    '#text': 8.0,
                    '@attrs': dict(unit='oz')
                },
            )
        )
        response = self.soap_api.execute('AddItem', item)
        print(response.dict())
        print(response.reply)
        return response

    async def create_inventory(self, product_data, listing_data, cross_listing):
        cond = 'NEW'
        images = []
        for image in listing_data['images']:
            if image['label'] == 'front':
                images.insert(0, image)
            else:
                images.append(image)

        item = dict(
            availability=dict(
                shipToLocationAvailability=dict(
                    quantity=1
                )
            ),
            condition=cond,
            conditionDescription=f"Item is in {listing_data['condition_name']} conditions and authenticated by a specialist",
            packageWeightAndSize=dict(
                dimensions=dict(
                    height=9.0,
                    length=9.0,
                    width=8.0,
                    unit='INCH'
                ),
                packageType='MAILING_BOX',
                weight=dict(
                    unit='OUNCE',
                    value=11.0
                ),
            ),
            product=dict(
                aspects={
                    "Brand": ["Funko"],
                    "Franchise": ["Pop"],
                    "Exclusivity": [product_data['product_profile'].get('exclusive', 'N/A')],
                    "Box Number": [product_data['product_profile'].get('box_number', 'N/A') or 'N/A'],
                    "License": [product_data['product_profile'].get('license', 'N/A')],
                },
                brand='Funko',
                title=cross_listing.title,
                mpn=product_data['item_number'] or (product_data['product_profile'].get('item_number', 'N/A') or 'N/A'),
                description=cross_listing.body,
                imageUrls=[image['public_url'] for image in images],
                upc=[product_data['upc']]
            )
        )
        res = await self.perform_request(self.client.create_or_replace_inventory_item, body=item, sku=listing_data['uuid'])

    async def create_offer(self, cross_listing, user):
        offer = dict(
            availableQuantity=1,
            format="FIXED_PRICE",
            categoryId=config['EBAY_CATEGORY_ID'],
            listingDescription=cross_listing.body,
            marketplaceId='EBAY_US',
            listingPolicies=dict(
                paymentPolicyId=user.ebay_payment_policy_id,
                returnPolicyId=user.ebay_return_policy_id,
                fulfillmentPolicyId=user.ebay_fulfillment_policy_id,
            ),
            merchantLocationKey=user.ebay_location_key,
            pricingSummary=dict(
                price=dict(value='%s' % (cross_listing.price_cents / 100, ), currency='USD')
            ),
            sku=cross_listing.sku
        )
        if cross_listing.external_id:
            res = await self.perform_request(self.client.update_offer, cross_listing.external_id, body=offer)
        else:
            res = await self.perform_request(self.client.create_offer, body=offer)
        return res

    async def get_offers(self, sku):
        res = await self.perform_request(self.client.get_offers, sku)
        return res

    async def get_offer(self, offer_id):
        res = await self.perform_request(self.client.get_offer, offer_id)
        return res

    async def publish_offer(self, cross_listing):
        res = await self.perform_request(self.client.publish_offer, cross_listing.external_id)
        return res

    async def withdraw_offer(self, cross_listing):
        res = await self.perform_request(self.client.withdraw_offer, cross_listing.external_id)
        return res

    async def delete_inventory(self):
        pass

    async def setup_location(self):
        location = dict(
            location=dict(
                address=dict(
                    addressLine1=config['WHATNOT_ADDRESS_LINE1'],
                    # addressLine2=config['WHATNOT_ADDRESS_LINE2'],
                    city=config['WHATNOT_ADDRESS_CITY'],
                    stateOrProvince=config['WHATNOT_ADDRESS_STATE'],
                    country='US',
                    postalCode=config['WHATNOT_ADDRESS_ZIP'],
                )
            ),
            locationInstructions="Items ship from here",
            name="Mountain View Address",
            merchantLocationStatus="ENABLED",
            locationTypes=[
                "WAREHOUSE"
            ]
        )
        result = await self.perform_request(self.client.create_inventory_location, location, 'WHATNOTMVCA20')
        return result

    async def get_default_category_tree_id(self):
        res = await self.client.get_default_category_tree_id('EBAY_US')
        return res['categoryTreeId']

    async def get_category_suggestion(self, query, tree_id=None):
        if tree_id is None:
            tree_id = await self.get_default_category_tree_id()
        data = await self.client.get_category_suggestions(tree_id, query)
        return data

    async def get_payment_policies(self):
        return await self.client.get_payment_policy('EBAY_US')

    async def get_fulfillment_policies(self):
        return await self.client.get_fulfillment_policies('EBAY_US')

    async def create_default_payment_policy(self):
        post_data = dict(
            categoryTypes=[
                dict(default=True, name='ALL_EXCLUDING_MOTORS_VEHICLES')
            ],
            description="Default policy",
            immediatePay=True,
            marketplaceId='EBAY_US',
            name='Default Payment Policy-3',
            paymentMethods=[
                dict(
                    bands=['AMERICAN_EXPRESS', 'MASTERCARD', 'VISA'],
                    paymentMethodType= "PAYPAL",
                    recipientAccountReference=dict(
                        referenceType='PAYPAL_EMAIL',
                        referenceId=config['SELLER_PAYPAL_EMAIL']
                    )
                )
            ]
        )
        result = await self.perform_request(self.client.create_payment_policy, body=post_data)
        return result

    async def get_return_policy(self):
        return await self.client.get_return_policy('EBAY_US')

    async def create_default_return_policy(self):
        post_data = dict(
            categoryTypes=[
                dict(default=True, name='ALL_EXCLUDING_MOTORS_VEHICLES')
            ],
            description="Default policy",
            extendedHolidayReturnsOffered=False,
            marketplaceId='EBAY_US',
            name='Default Return Policy',
            refundMethods="CASH_BACK",
            returnInstructions="Please contact us on support@whatnot.com",
            returnMethod="EXCHANGE",
            returnPeriod=dict(
                unit="DAY",
                value=30,
            ),
            returnsAccepted=True,
            returnShippingCostPayer="BUYER"
        )
        result = await self.perform_request(self.client.create_return_policy, body=post_data)
        return result

    async def create_default_fulfillment_policy(self, rate_table_id=None):
        post_data = dict(
            categoryTypes=[
                dict(name='ALL_EXCLUDING_MOTORS_VEHICLES')
            ],
            marketplaceId='EBAY_US',
            description="Default policy",
            # globalShipping=False,
            handlingTime=dict(
                unit="DAY",
                value="5"
            ),
            localPickup=False,
            name='Default Fulfillment Policy',
            shippingOptions=[
                dict(
                    costType="CALCULATED",
                    optionType='DOMESTIC',
                    packageHandlingCost=dict(
                        currency='USD',
                        value='2.50'
                    ),
                    shippingServices=[dict(
                        shippingCarrierCode='USPS',
                        shippingServiceCode='USPSFirstClass',
                        buyerResponsibleForShipping=True,
                        freeShipping=False
                    )]
                )
            ]
        )
        result = await self.perform_request(self.client.create_fulfillment_policy, body=post_data)
        return result

    async def get_order(self, order_id):
        result = await self.perform_request(self.client.get_order, order_id)
        return result

    async def get_orders(self, since):
        result = await self.perform_request(self.client.get_orders, since)
        return result

    async def get_shipping_rates(self, package_info, address_from, address_to, orders=[], **kwargs):
        ship_from_address = {
            'addressLine1': address_from['line1'],
            'addressLine2': address_from.get('line2', None),
            'city': address_from['city'],
            'stateOrProvince': address_from['state'],
            'countryCode': 'US',
            'postalCode': address_from['postal_code'],
        }
        ship_to_address = {
            'addressLine1': address_to['line1'],
            'addressLine2': address_to.get('line2', None),
            'city': address_to['city'],
            'stateOrProvince': address_to['state'],
            'countryCode': address_to.get('country_code', 'US'),
            'postalCode': address_to['postal_code'],
        }
        if not ship_from_address['addressLine2']:
            ship_from_address.pop('addressLine2')
        if not ship_to_address['addressLine2']:
            ship_to_address.pop('addressLine2')
        body = {
            'orders': [ {'orderId': order['order_id'], 'channel': order['channel']}
                for order in orders
            ],
            'packageSpecification': {
                'dimensions': {
                    'height': package_info['height'],
                    'width': package_info['width'],
                    'length': package_info['length'],
                    'unit': 'INCH'
                },
                'weight': {
                    'unit': 'OUNCE',
                    'value': package_info['weight']
                }
            },
            'shipFrom': {
                'companyName': address_from['company_name'],
                'contactAddress': ship_from_address,
                'primaryPhone': {
                    'phoneNumber': address_from['phone']
                }
            },
            'shipTo': {
                'fullName': address_to['full_name'],
                'contactAddress': ship_to_address,
                'primaryPhone': {
                    'phoneNumber': address_to['phone']
                }
            },
        }

        result = await self.perform_request(self.client.create_shipping_quotes, body)
        return result

    async def create_shipping_label(self, quote_id, rate_id, size='4x6'):
        body = {
            'labelCustomMessage': 'Whatnot, the market place for authenticated collectables',
            'labelSize': size,
            'rateId': rate_id,
            'shippingQuoteId': quote_id,
        }

        result = await self.perform_request(self.client.create_shipping_from_quote, body)
        return result
