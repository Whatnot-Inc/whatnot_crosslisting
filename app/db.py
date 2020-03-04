from datetime import datetime as dt
from datetime import timedelta
from collections import namedtuple
import ssl

import asyncpgsa
from sqlalchemy import (
    MetaData, Table, Column, ForeignKey,
    Integer, String, DateTime
)
from sqlalchemy.sql.sqltypes import JSON, Text
from sqlalchemy.sql import select, and_
import certifi

metadata = MetaData()


cross_listings = Table(
    'cross_listings', metadata,

    Column('id', Integer, primary_key=True),
    Column('listing_id', Integer, nullable=False),
    Column('product_id', Integer, nullable=False),
    Column('product_upc', String, nullable=False),
    Column('product_name', String, nullable=False),
    Column('marketplace', String(250), nullable=False),
    Column('price_cents', Integer),
    Column('external_id', String),
    Column('sku', String),
    Column('secondary_external_id', String),
    Column('title', String(200)),
    Column('body', Text),
    Column('status', String(128), nullable=False),
    Column('operational_status', String(128), nullable=False),
    Column('updated_at', DateTime, index=True, default=dt.utcnow),
    Column('created_at', DateTime, index=True, default=dt.utcnow),
)

users = Table(
    'users', metadata,
    Column('id', Integer, primary_key=True),
    Column('email', String, unique=True),
    Column('external_id', String),
    Column('ebay_token', String),
    Column('ebay_refresh_token', String),
    Column('ebay_payment_policy_id', String),
    Column('ebay_fulfillment_policy_id', String),
    Column('ebay_return_policy_id', String),
    Column('ebay_location_key', String),
    Column('created_at', DateTime, index=True, default=dt.utcnow),
    Column('updated_at', DateTime, index=True, default=dt.utcnow),
)

operations = Table(
    'operations', metadata,

    Column('id', Integer, primary_key=True),
    # Column('parent_id', Integer, ForeignKey('operations.id'), index=True),

    # Column('listing_id', Integer, nullable=False, index=True),
    Column('cross_listing_id', Integer, ForeignKey('cross_listings.id'), index=True),


    Column('name', String, nullable=False),
    Column('status', String, nullable=False),
    Column('workflow_specs', JSON),
    Column('workflow_instance', JSON),

    Column('updated_at', DateTime, index=True, default=dt.utcnow),
    Column('created_at', DateTime, index=True, default=dt.utcnow),
)


async def init_db(app=None, config=None):
    config = (app['config'] if app else config) or {}
    dsn = config['DATABASE_URL']
    ctx = ssl.create_default_context(capath=certifi.where())
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    pool = await asyncpgsa.create_pool(
        dsn=dsn,
        min_size=2,
        ssl=ctx
    )
    if app:
        app['db_pool'] = pool
    return pool

class Repository:
    table = None

    def __init__(self, connection):
        self.conn = connection

    async def get_by_id(self, obj_id):
        return await self.get_by(id=obj_id)

    async def get_by(self, **kwargs):
        return await self.conn.fetchrow(
            self.table
            .select()
            .where(and_(*[getattr(self.table.c, field_name) == field_val for field_name, field_val in kwargs.items()]))
        )

    async def filter_by(self, **kwargs):
        return await self.conn.fetch(
            self.table
            .select()
            .where(and_(*[getattr(self.table.c, field_name) == field_val for field_name, field_val in kwargs.items()]))
        )

    async def first(self):
        return await self.conn.fetchrow(
            self.table
            .select()
            .limit(1)
        )

    async def update(self, obj):
        if type(obj) == dict:
            values = obj
        else:
            values = obj.to_dict()
        obj_id = values.pop('id')
        query = self.table.update().values(values)\
                .where(self.table.c.id == obj_id)
        row = await self.conn.execute(query)
        # self.conn.commit()
        return ('failed' not in row)

    def delete(self, obj):
        if type(obj) == dict:
            obj = namedtuple('DeleteObject', obj.keys())(**obj)
        pass

    async def create(self, obj):
        if type(obj) == dict:
            insert_dict = obj
        else:
            print(obj)
            insert_dict = obj.to_dict()

        insert_dict.pop('id', None)
        print(insert_dict)
        query = self.table.insert().values(insert_dict)\
                .returning(*[getattr(self.table.c, column) for column in self.table.columns.keys()])

        return await self.conn.fetchrow(query)

class CrossListingRepository(Repository):
    table=cross_listings

    async def get_active_in_the_last(self, days=30):
        query = cross_listings.select().where(
            and_(
                cross_listings.c.updated_at < dt.now() - timedelta(days=days),
                cross_listings.c.status.in_(['active', 'disabled']),
                cross_listings.c.operational_status == 'offer_published'
            )
        )
        print(asyncpgsa.compile_query(query))
        return await self.conn.fetch(
            query
        )

class OperationsRepository(Repository):
    table=operations

class UserRepository(Repository):
    table=users
