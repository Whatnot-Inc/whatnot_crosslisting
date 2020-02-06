from aiotasks import build_manager
from .utils import send_task
from .settings import load_config

config = load_config()

manager = build_manager(dsn=f"redis://{config['REDIS_HOST']}:{config['REDIS_PORT']}/")

dsn = config['DATABASE_URL']
db_pool = await asyncpgsa.create_pool(dsn=dsn)

async def create_marketplace_listing(market_place, **data):
    listing_id = data['listing_id']
    price_cents = data['price_cents']
