class BaseEvent(object):
    name='Event'
    def __init__(self, data):
        if not all([field in data for field in self.required_fields]):
            raise Exception('Invalid event data. Missing fields.')
        self.data = data

class CreateListing(BaseEvent):
    name='CreateListing'
    required_fields = ['listing', 'marketplaces', 'price_cents', 'condition']

class DeactivateListing(BaseEvent):
    name='DeactivateListing'
    required_fields = ['listing', 'marketplaces']


class UpdateListing(BaseEvent):
    name='UpdateListing'
    required_fields = ['listing_id', 'price_cents', 'condition']
