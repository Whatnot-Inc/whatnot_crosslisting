import tempfile
import base64
from urllib.parse import urlencode

import asyncio
import aiohttp

class RestResponseError(Exception):
    def __init__(self, status, content, json_c, *args, **kwargs):
        self.status_code = status
        self.content = content,
        self.json = json_c
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"<RestResponseError status_code='{self.status_code}', content='{self.content}'>"

class BaseRestClient:
    def __init__(self, cache=None, bearer_token=None, basic_auth=None):
        self.cache = cache
        self.bearer_token = bearer_token
        self.basic_auth = basic_auth

    def login(self, part_a, part_b):
        raise NotImplementedError

    def oauth_login(self, token):
        self.bearer_token = token
        print

    @property
    def default_headers(self):
        headers = {
            'Content-Type': 'application/json',
            'Content-Language': 'en-US',
            'Accept': 'application/json',
        }
        if self.bearer_token:
            headers['Authorization'] = 'Bearer %s' % self.bearer_token
        elif self.basic_auth:
            headers['Authorization'] = f"Basic {self.basic_auth}"
        return headers

    def get_dict_body(self, body):
        if body is None:
            return body
        return body.to_dict() if type(body) != dict else body

    async def _put(self, url, body, headers={}):
        print(url)
        # print({**self.default_headers, **headers})
        print(body)
        async with aiohttp.ClientSession() as client:
            try:
                async with client.put(url, json=self.get_dict_body(body), headers={**self.default_headers, **headers}) as resp:
                    print(resp.status)
                    if resp.status  > 399:
                        d = await resp.content.read()
                        j = await resp.json()
                        raise RestResponseError(resp.status, d, j)
                    return await resp.json()
            except aiohttp.ClientPayloadError as ex:
                print(f'ClientPayloadError {ex.status}. Message: {ex.message}', ex)
                raise ex
            except aiohttp.ClientError as ex:
                print('ClientError',ex)
                raise ex

    async def _post(self, url, body=None, headers={}):
        print(url)
        # print({**self.default_headers, **headers})
        print(body)
        async with aiohttp.ClientSession() as client:
            try:
                async with client.post(url, json=self.get_dict_body(body), headers={**self.default_headers, **headers}) as resp:
                    print(resp.status)
                    if resp.status  > 399:
                        d = await resp.content.read()
                        j = await resp.json()
                        raise RestResponseError(resp.status, d, j)
                    return await resp.json()
            except aiohttp.ClientPayloadError as ex:
                print(f'ClientPayloadError {ex.status}. Message: {ex.message}', ex)
                raise ex
            except aiohttp.ClientError as ex:
                print('ClientError',ex)
                raise ex

    async def _get(self, url, headers={}):
        print(url)
        # print({**self.default_headers, **headers})
        async with aiohttp.ClientSession() as client:
            try:
                async with client.get(url, headers={**self.default_headers, **headers}) as resp:
                    print(resp.status)
                    if resp.status  > 399:
                        d = await resp.content.read()
                        j = await resp.json()
                        raise RestResponseError(resp.status, d, j)
                    return await resp.json()
            except aiohttp.ClientPayloadError as ex:
                print(f'Client PayloadError {ex.status}. Message: {ex.message}', ex)
                raise ex
            except aiohttp.ClientError as ex:
                print('ClientError',ex)
                raise ex
