from datetime import datetime
import time
from app.clients.ebay import EBayClient, TokenExpiredError, RestResponseError
from app.enums import EbayOperationsStates, CrossListingStates
class BaseListingCreatorAdaptor:
    def __init__(self, config):
        self.config = config
        super().__init__()

    async def create_listing(self, listing_data, product_data):
        raise NotImplementedError

    async def deactivate_listing(self, cross_listing):
        raise NotImplementedError

    async def get_title(self, listing_data, product_data):
        s = [f"Authentic {product_data['name']} Funko Pop"]

        if product_data['product_profile']['exclusivity']:
            s.append(f"{product_data['product_profile']['exclusivity']}")
            s.append("Exclusive ")

        if product_data['product_profile']['box_number']:
            s.append(f"#{product_data['product_profile']['box_number']}")

        s.append(f"| {listing_data['condition_name']} Condition.")

        if product_data['product_profile']['license']:
            s.append(product_data['product_profile']['license'])

        s_o = " ".join(s)
        while len(s_o) > 80:
            s.pop()
            s_o = " ".join(s)
        return s_o

    async def get_body(self, listing_data, product_data):
        name = [product_data['name']]
        if product_data['product_profile']['exclusivity']:
            name.append(f"{product_data['product_profile']['exclusivity']}")
            name.append("Exclusive ")
        box_n = ''
        if product_data['product_profile']['box_number']:
            box_n = f" #{product_data['product_profile']['box_number']}"
        release_date = datetime.fromisoformat(product_data['release_date'])
        return f'''
            <h1>{" ".join(name)}</h1>
            <h2>THE ITEM</h2>
            <p>
            You’re purchasing an authentic {listing_data['condition_name']} Condition {" ".join(name)} Funko Pop{box_n}.
            Please check the photos to make a judgement call on the box condition yourself. The Funko pictured is the one you will receive.
            </p>
            <p>
            Every Funko Pop we sell is inspected by our team of experts to ensure it’s authenticity.
            </p>

            <h2>PACKAGING</h2>
            <p>
            All regular-sized pops are put in a protector, wrapped in bubble wrap and surrounded by packing peanuts in an 8x8x8 box with a fragile sticker on it.
            We take packaging very seriously. There’s nothing worse than anxiously waiting for your new pop only to find out that it’s crushed!
            </p>

            <h2>SHIPPING</h2>
            <p>
            Due to our authentication process, we typically ship things to you 7 days after payment, but it may take a bit longer.
            If you want super fast shipping, we’re probably not the place to purchase from.
            However, if you want an authentic pop, well packaged and cared for, we’re here for you!
            </p>

            <p>
            For international shipping, you are responsible for all duties and taxes on the item.
            </p>

            <h2>ABOUT WHATNOT INC.</h2>
            <p>
            Whatnot Inc. is an online store where people can buy and sell authentic Funko Pops. Every Funko sold on Whatnot is hand verified by an expert.
            </p>

            <h2>RETURNS</h2>
            <p>
            We offer free returns if you’re unhappy with your purchase.
            </p>

            <h2>ADDITIONAL ITEM DETAILS</h2>
            License: {product_data['product_profile']['license']} <br />
            Box Number: {product_data['product_profile']['box_number']} <br />
            Exclusivity: {product_data['product_profile']['exclusivity']} <br />
            Is chase: {'Yes' if product_data['product_profile']['is_chase'] else 'No'} <br />
            Release date: {release_date.strftime("%B %Y")} <br />

        '''


class SimpleEbayListingCreatorAdaptor(BaseListingCreatorAdaptor):
    def __init__(self, config, repository):
        super().__init__(config)
        self.ebay_client = EBayClient(self.config)
        self.repository = repository

    async def create_soap_listing(self, listing_data, product_data, cross_listing, user):
        await self.ebay_client.login(user)
        try:
            cross_listing.operational_status = EbayOperationsStates.CREATING_INVENTORY.value
            await self.repository.update({'id': cross_listing.id, 'operational_status': cross_listing.operational_status})

            inventory = await self.add_item(product_data, listing_data, cross_listing, user)
            print(inventory)
            cross_listing.secondary_external_id = inventory['itemID']
            cross_listing.operational_status = EbayOperationsStates.OFFER_PUBLISHED.value
            cross_listing.status = CrossListingStates.ACTIVE.value
            cross_listing.updated_at = datetime.now()
            await self.repository.update(cross_listing.to_dict())
            return cross_listing
        except:
            import traceback
            traceback.print_exc()

    async def create_listing(self, listing_data, product_data, cross_listing, user):
        await self.ebay_client.login(user)
        # policy = await self.ebay_client.create_default_payment_policy()
        # print(policy)
        # location = await self.ebay_client.setup_location()
        # print(location)
        try:
            cross_listing.operational_status = EbayOperationsStates.CREATING_INVENTORY.value
            await self.repository.update({'id': cross_listing.id, 'operational_status': cross_listing.operational_status})

            inventory = await self.create_inventory(product_data, listing_data, cross_listing, user)

            cross_listing.operational_status = EbayOperationsStates.CREATING_OFFER.value
            cross_listing.status = CrossListingStates.PUBLISHING.value
            await self.repository.update({'id': cross_listing.id, 'operational_status': cross_listing.operational_status, 'status': cross_listing.status})

            offer = await self.create_offer(cross_listing, user)
            if cross_listing.external_id is None:
                cross_listing.external_id = offer['offerId']
                cross_listing.operational_status = EbayOperationsStates.OFFER_CREATED.value
                cross_listing.updated_at = datetime.now()
                await self.repository.update(cross_listing.to_dict())

            # if cross_listing.secondary_external_id is None:
            cross_listing.operational_status = EbayOperationsStates.PUBLISHING_OFFER.value
            await self.repository.update({'id': cross_listing.id, 'operational_status': cross_listing.operational_status})
            try:
                publish = await self.publish_offer(cross_listing)
                cross_listing.secondary_external_id = publish['listingId']
                cross_listing.operational_status = EbayOperationsStates.OFFER_PUBLISHED.value
                cross_listing.status = CrossListingStates.ACTIVE.value
                cross_listing.updated_at = datetime.now()
                await self.repository.update(cross_listing.to_dict())
            except RestResponseError as rex:
                print(rex)
                cross_listing.status = CrossListingStates.DISABLED.value
                cross_listing.operational_status = EbayOperationsStates.OFFER_CREATED.value
                cross_listing.updated_at = datetime.now()
                await self.repository.update({
                    'id': cross_listing.id,
                    'status': cross_listing.status,
                    'operational_status': cross_listing.operational_status,
                    'updated_at': cross_listing.updated_at
                })

            return cross_listing
        except RestResponseError as ex:
            print("Failed to create inventory")
            print(ex)
            cross_listing.status = CrossListingStates.DISABLED.value
            await self.repository.update({'id': cross_listing.id, 'status': cross_listing.status})
            raise ex

    async def deactivate_listing(self, cross_listing, user):
        await self.ebay_client.login(user)
        # res = await self.ebay_client.get_offers(cross_listing.sku)
        # print(res)
        result = await self.ebay_client.withdraw_offer(cross_listing)
        cross_listing.status = CrossListingStates.DISABLED.value
        await self.repository.update({'id': cross_listing.id, 'status': cross_listing.status})

        return result

    async def add_item(self, product_data, listing_data, cross_listing, user):
        result = self.ebay_client.add_item(product_data, listing_data, cross_listing)
        return result

    async def create_inventory(self, product_data, listing_data, cross_listing, user):
        result = await self.ebay_client.create_inventory(product_data, listing_data, cross_listing)
        return result

    async def create_offer(self, cross_listing, user):
        result = await self.ebay_client.create_offer(cross_listing, user)
        return result

    async def publish_offer(self, cross_listing):
        result = await self.ebay_client.publish_offer(cross_listing)
        return result
