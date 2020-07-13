import asyncio
from app.services import UserManager, OrderManager, ListingManager
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
        print("Initialize order manager")
        order_mgmt = OrderManager(user, None, db_conn=db_conn, config=config)
        print("Starting mainloop")
        while True:
            print("Logging into ebay")
            await ebay_client.login(user)
            print("Pull and process orders")
            await order_mgmt.pull_recent_orders(ebay_client, last_x_hours=5)
            print("Resting for a bit")
            await asyncio.sleep(15)
            print("Rested...")
            user = await user_mgmt.update_ebay_token(user)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    loop.close()
