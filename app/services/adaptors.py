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
        s = [f"Funko Pop! {product_data['name']}"]

        if product_data['product_profile']['exclusivity']:
            s.append(f"{product_data['product_profile']['exclusivity']}")
            s.append("Exclusive !")

        if product_data['product_profile']['box_number']:
            s.append(f"#{product_data['product_profile']['box_number']}")

        if product_data['product_profile']['license']:
            s.append(product_data['product_profile']['license'])

        s_o = " ".join(s)
        while len(s_o) > 80:
            s.pop()
            s_o = " ".join(s)
        return s_o

    async def get_body(self, listing_data, product_data):
        return f"<h1>This is a {listing_data['condition_name']} condition {product_data['name']} Funko Pop</h1>. All products sold by Whatnot goes through an in-depth inspections to attest their authenticity and rate its condition."

class SimpleEbayListingCreatorAdaptor(BaseListingCreatorAdaptor):
    def __init__(self, config, repository):
        super().__init__(config)
        self.ebay_client = EBayClient(self.config)
        self.repository = repository

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
                await self.repository.update(cross_listing.to_dict())

            # if cross_listing.secondary_external_id is None:
            cross_listing.operational_status = EbayOperationsStates.PUBLISHING_OFFER.value
            await self.repository.update({'id': cross_listing.id, 'operational_status': cross_listing.operational_status})
            try:
                publish = await self.publish_offer(cross_listing)
                cross_listing.secondary_external_id = publish['listingId']
                cross_listing.operational_status = EbayOperationsStates.OFFER_PUBLISHED.value
                cross_listing.status = CrossListingStates.ACTIVE.value
                await self.repository.update(cross_listing.to_dict())
            except RestResponseError as rex:
                print(rex)
                cross_listing.status = CrossListingStates.DISABLED.value
                cross_listing.operational_status = EbayOperationsStates.OFFER_CREATED.value
                await self.repository.update({'id': cross_listing.id, 'status': cross_listing.status, 'operational_status': cross_listing.operational_status})

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

    async def create_inventory(self, product_data, listing_data, cross_listing, user):
        result = await self.ebay_client.create_inventory(product_data, listing_data, cross_listing)
        return result

    async def create_offer(self, cross_listing, user):
        result = await self.ebay_client.create_offer(cross_listing, user)
        return result

    async def publish_offer(self, cross_listing):
        result = await self.ebay_client.publish_offer(cross_listing)
        return result
