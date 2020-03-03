import json
import aiohttp_jinja2
from aiohttp import web

# import db
from . import events
from .services import EventProcessor, UserManager, ListingManager, OrderManager, LogisticManager
from .clients.ebay import get_ebay_conscent_link
from .db import CrossListingRepository
from .models import CrossListing

async def index(request):
    return web.Response(text="Ok")

async def get_ebay_link(request):
    config = request.app['config']
    response = {
        'url': get_ebay_conscent_link(config['EBAY_CLIENT_ID'], config['EBAY_RU_NAME'])
    }
    return web.json_response(response, status=200)

async def suggest_category(request):
    config = request.app['config']
    s = request.query['q']
    async with request.app['db_pool'].acquire() as conn:
        svc = ListingManager('ebay', {}, {}, db_conn=conn, config=config)
        res = await svc.suggest_category(s)
        return web.json_response(data=res)

async def ebay_connect_response(request):
    config = request.app['config']
    code = request.query['code']
    async with request.app['db_pool'].acquire() as conn:
        manager = UserManager(db_conn=conn, config=config)
        user = await manager.get_or_create_default_user()
        await manager.update_ebay_token(user, code)

    return web.Response(text='Ebay account linked')

async def event(request):
    config = request.app['config']
    data = await request.json()

    if not hasattr(events, data['event']):
        return web.Response(status=400)

    event = getattr(events, data['event'])(data['data'])

    async with request.app['db_pool'].acquire() as conn:
        processor = EventProcessor(event, db_conn=conn, config=config)
        try:
            res = await processor.process()
            res = web.json_response(text=res.to_json(), status=201)
            return res
        except Exception as ex:
            import traceback
            traceback.print_exc()
            print(ex)
            return web.Response(text=str(ex), status=500)

async def set_user_payment_policy(request):
    config = request.app['config']
    data = await request.json()
    async with request.app['db_pool'].acquire() as conn:
        mgmt = UserManager(db_conn=conn, config=config)
        user = await mgmt.get_or_create_default_user()
        policy = await mgmt.create_or_update_default_payment_policy(user, data)
        return web.json_response(data=policy, status=200)

async def set_user_fulfillment_policy(request):
    config = request.app['config']
    data = await request.json()
    async with request.app['db_pool'].acquire() as conn:
        mgmt = UserManager(db_conn=conn, config=config)
        user = await mgmt.get_or_create_default_user()
        policy = await mgmt.create_or_update_default_fulfillment_policy(user, data)
        return web.json_response(data=policy, status=200)

async def set_user_return_policy(request):
    config = request.app['config']
    data = await request.json()
    async with request.app['db_pool'].acquire() as conn:
        mgmt = UserManager(db_conn=conn, config=config)
        user = await mgmt.get_or_create_default_user()
        policy = await mgmt.create_or_update_default_return_policy(user, data)
        return web.json_response(data=policy, status=200)

async def set_user_location(request):
    config = request.app['config']
    data = await request.json()
    async with request.app['db_pool'].acquire() as conn:
        mgmt = UserManager(db_conn=conn, config=config)
        user = await mgmt.get_or_create_default_user()
        location_key = data.pop('location_key', user.ebay_location_key)
        location = await mgmt.create_or_update_default_location(user, data, location_key)
        return web.json_response(data=location, status=200)

async def get_cross_listings(request):
    config = request.app['config']
    listing_id = int(request.match_info['listing_id'])
    async with request.app['db_pool'].acquire() as conn:
        repository = CrossListingRepository(conn)
        response = web.StreamResponse(
            status=200,
            reason='OK',
            headers={'Content-Type': 'application/json'},
        )
        await response.prepare(request)
        await response.write('['.encode('utf-8'))
        is_first = True
        for record in await repository.filter_by(listing_id=listing_id):
            if not is_first:
                await response.write(','.encode('utf-8'))
            cl = CrossListing(**dict(record))
            await response.write(cl.to_json().encode('utf-8'))
            is_first = False
        await response.write(']'.encode('utf-8'))
        await response.write_eof()
        return response

async def ebay_callback(request):
    config = request.app['config']
    data = await request.read()
    print(data)
    json_data = json.loads(data.decode('utf8'))
    secondary_external_id = int(json_data['secondary_external_id'])
    async with request.app['db_pool'].acquire() as conn:
        mgmt = UserManager(db_conn=conn, config=config)
        user = await mgmt.get_or_create_default_user()
        user = await mgmt.update_ebay_token(user)

        svc = OrderManager(user, secondary_external_id, db_conn=conn, config=config)
        await svc.setup()

        d = await svc.create_order(json_data)
        return web.json_response(data=d)

async def get_shipping_rates(request):
    config = request.app['config']
    data = await request.json()
    async with request.app['db_pool'].acquire() as conn:
        mgmt = UserManager(db_conn=conn, config=config)
        user = await mgmt.get_or_create_default_user()
        user = await mgmt.update_ebay_token(user)

        order = {'order_id': data['order_id'], 'channel': data['order_channel']}

        svc = LogisticManager(user, db_conn=conn, config=config)
        res = await svc.quote_outgoing(data['address_to'], order )
        return res
