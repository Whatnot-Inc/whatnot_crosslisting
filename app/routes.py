from .views import index, event, get_ebay_link, ebay_connect_response, set_user_fulfillment_policy, suggest_category
from .views import set_user_payment_policy, set_user_location, set_user_return_policy, get_cross_listings, ebay_callback
from .views import get_shipping_rates

def setup_routes(app):
    app.router.add_get('/', index, name='index')
    app.router.add_post('/api/event', event, name='event')
    app.router.add_get('/api/setup/ebay/link', get_ebay_link, name='get_ebay_link')
    app.router.add_get('/public/setup/ebay/link/callback', ebay_connect_response, name='ebay_connect_response')
    app.router.add_post('/api/user/1/fulfillment_policy', set_user_fulfillment_policy, name='set_user_fulfillment_policy')
    app.router.add_post('/api/user/1/payment_policy', set_user_payment_policy, name='set_user_payment_policy')
    app.router.add_post('/api/user/1/return_policy', set_user_return_policy, name='set_user_return_policy')
    app.router.add_post('/api/user/1/address', set_user_location, name='set_user_location')
    app.router.add_get('/api/listings/{listing_id}', get_cross_listings, name='get_cross_listings')
    app.router.add_get('/api/categories/suggest', suggest_category, name='suggest_category')
    app.router.add_post('/public/ebay_notifications', ebay_callback, name='ebay_callback')
    app.router.add_post('/api/shipment_quote', get_shipping_rates, name='get_shipping_rates')
