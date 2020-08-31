import asyncio
from app.services import UserManager, OrderManager, ListingManager
from app.enums import CrossListingStates
from app.settings import load_config
from app.clients.ebay import EBayClient
from app.db import init_db

config = load_config()

async def main(loop):
    print("Initializing db")
    db_pool = await init_db(config=config)
    print("Initializing Crosslisting's eBay Client")
    ebay_client = EBayClient(config)
    print("Acquiring connection")
    async with db_pool.acquire() as db_conn:
        print("Initialize user manager")
        user_mgmt = UserManager(db_conn=db_conn, config=config)
        print("Get single user")
        user = await user_mgmt.get_or_create_default_user()
        print("Update user's token")
        user = await user_mgmt.update_ebay_token(user)
        print("Initialize listing manager")
        listing_mgmt = ListingManager('ebay', None, None, db_conn=db_conn, config=config)
        print("Starting mainloop")
        for record in await listing_mgmt.repository.filter_by(status=CrossListingStates.ACTIVE.value):
            print(f"Deactivating: {record}")
            try:
                await listing_mgmt.deactivate(record)
            except:
                print(f"Failed to deactivate: {record}")



if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    loop.close()
