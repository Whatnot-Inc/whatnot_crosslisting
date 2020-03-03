from datetime import datetime, timedelta
from collections import namedtuple
from typing import Optional

from marshmallow import Schema, fields, post_load

from dataclasses import dataclass
from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class CrossListing:
    listing_id: int
    marketplace: str
    price_cents: int
    sku: str
    product_id: int = None
    product_upc: str = None
    product_name: str = None
    id: int = None
    external_id: str = None
    secondary_external_id: str = None
    title: str = None
    body: str = None
    status: str = None
    operational_status: str = None
    created_at: datetime = None
    updated_at: datetime = None


# CrossListing = namedtuple('CrossListing', crosslisting_schema.fields.keys())
@dataclass_json
@dataclass
class User:
    email: str
    id: int = None
    external_id: str = None
    secondary_external_id: str = None
    ebay_token: str = None
    ebay_refresh_token: str = None
    ebay_payment_policy_id: str = None
    ebay_fulfillment_policy_id: str = None
    ebay_return_policy_id: str = None
    ebay_location_key: str = None
    created_at: datetime = None
    updated_at: datetime = None

# User = namedtuple('User', user_schema.fields.keys())
