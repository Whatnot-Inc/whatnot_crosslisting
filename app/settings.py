import os

from dotenv import load_dotenv

load_dotenv()

PACKAGE_NAME = 'whatnot_crosslistings'


def load_config():
    return {
        'DATABASE_URL': os.environ['DATABASE_URL'], # "postgresql://{user}:{password}@{host}:{port}/{database}"
        'REDIS_HOST': os.environ['REDIS_HOST'],
        'REDIS_PORT': os.environ['REDIS_PORT'],
        'REDIS_PWD': os.environ['REDIS_PWD'],
        'JWT_SECRET': os.environ.get('JWT_SECRET', 'Omg!ItsGMO:(237878%ˆ%$7869#!9206KJjbAJYuglAli7=12=eyj5td5125ihj'),
        'CREDS_APPID': os.environ.get('CREDS_APPID', 'WhatnotI-whatnotc-PRD-7ce6fb270-c2203f95'),
        'CREDS_DEVID': os.environ.get('CREDS_DEVID', '4c7a3cf9-0528-4aa1-96ed-32b54f441fbd'),
        'CREDS_CERTID': os.environ.get('CREDS_CERTID', 'PRD-ce6fb270714b-3bc2-44f3-b7ca-bd1d'),
        'WHATNOT_ADDRESS_LINE1': os.environ.get('WHATNOT_ADDRESS_LINE1', '1577 Latham St.'),
        'WHATNOT_ADDRESS_LINE2': os.environ.get('WHATNOT_ADDRESS_LINE2', ''),
        'WHATNOT_ADDRESS_CITY': os.environ.get('WHATNOT_ADDRESS_CITY', 'Mountain View'),
        'WHATNOT_ADDRESS_STATE': os.environ.get('WHATNOT_ADDRESS_STATE', 'CA'),
        'WHATNOT_ADDRESS_ZIP': os.environ.get('WHATNOT_ADDRESS_ZIP', '94041'),
        'WHATNOT_API_BASE_URL': os.environ.get('WHATNOT_API_BASE_URL', 'https://stage-api.whatnot.com'),
        'EBAY_API_BASE_URL': os.environ.get('EBAY_API_BASE_URL', 'https://api.sandbox.ebay.com'),
        'EBAY_API_AUTH_BASE_URL': os.environ.get('EBAY_API_AUTH_BASE_URL', 'https://auth.sandbox.ebay.com'),
        'EBAY_CLIENT_ID': os.environ['EBAY_CLIENT_ID'],
        'EBAY_CLIENT_SECRET': os.environ['EBAY_CLIENT_SECRET'],
        'EBAY_CATEGORY_ID': os.environ['EBAY_CATEGORY_ID'],
        'EBAY_RETURN_POLICY_ID': os.environ['EBAY_RETURN_POLICY_ID'],
        'EBAY_FULFILLMENT_POLICY_ID': os.environ['EBAY_FULFILLMENT_POLICY_ID'],
        'EBAY_PAYMENT_POLICY_ID': os.environ['EBAY_PAYMENT_POLICY_ID'],
        'EBAY_RU_NAME': os.environ['EBAY_RU_NAME'],
        'WHATNOT_USERNAME': os.environ['WHATNOT_USERNAME'],
        'WHATNOT_PASSWORD': os.environ['WHATNOT_PASSWORD'],
        'SELLER_PAYPAL_EMAIL': os.environ.get('SELLER_PAYPAL_EMAIL', 'sb-zp01j778684@business.example.com'),
        'SLACK_API_TOKEN': os.environ.get('SLACK_API_TOKEN')
    }
