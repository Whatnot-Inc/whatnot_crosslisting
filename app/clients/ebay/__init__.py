from app.settings import load_config
from .rest import EbayRestClient, RestResponseError
config = load_config()

def get_ebay_conscent_link(client_id, redirect_uri):
    return f"https://auth.sandbox.ebay.com/oauth2/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope=https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/buy.order.readonly https://api.ebay.com/oauth/api_scope/buy.guest.order https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.analytics.readonly https://api.ebay.com/oauth/api_scope/sell.marketplace.insights.readonly https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly https://api.ebay.com/oauth/api_scope/buy.shopping.cart https://api.ebay.com/oauth/api_scope/buy.offer.auction https://api.ebay.com/oauth/api_scope/commerce.identity.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.email.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.phone.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.address.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.name.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.status.readonly https://api.ebay.com/oauth/api_scope/sell.finances https://api.ebay.com/oauth/api_scope/sell.item.draft https://api.ebay.com/oauth/api_scope/sell.payment.dispute https://api.ebay.com/oauth/api_scope/sell.item"

class TokenExpiredError(Exception):
    pass

class EBayClient:
    def __init__(self, config):
        self.__api_instance = None
        self.config = config
        self.client = EbayRestClient()

    async def login(self, user):
        self.client.oauth_login(user.ebay_token)

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

    async def create_inventory(self, product_data, listing_data, cross_listing):
        item = dict(
            availability=dict(
                shipToLocationAvailability=dict(
                    quantity=1
                )
            ),
            condition='NEW_OTHER',
            conditionDescription=listing_data['condition_name'],
            packageWeightAndSize=dict(
                dimensions=dict(
                    height=5.0,
                    length=5.0,
                    width=5.0,
                    unit='INCH'
                ),
                packageType='MAILING_BOX',
                weight=dict(
                    unit='OUNCE',
                    value=1.0
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
                imageUrls=[image['public_url'] for image in listing_data['images']],
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
