import aiohttp
import asyncio
import atexit
from aiohttp_socks import ProxyType, ProxyConnector, ChainProxyConnector

__all__=["APIBase"]

class A(object):
    """Inheriting this class allows you to define an async __init__.

    So you can create objects by doing something like `await MyClass(params)`
    """

    async def __new__(cls, *a, **kw):
        instance = super().__new__(cls)
        await instance.__init__(*a, **kw)
        return instance

    async def __init__(self):
        pass

    def __await__(self):
        pass


class APIBase(A):
    base_url = ''
    headers = {'User-Agent': 'Mozilla/5.0'}
    cookies = None
    timeout = 5
    proxy = ''

    async def __init__(self, proxy=''):
        await super(APIBase, self).__init__()
        self.proxy = proxy
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        if proxy:
            connector = ProxyConnector.from_url(proxy)
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        else:
            self._session = aiohttp.ClientSession(timeout=timeout)
        atexit.register(self._shutdown)

    async def request(self, *args, **kwargs):
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        if 'timeout' not in kwargs:
            kwargs['timeout'] = timeout
        if self.headers:
            if 'headers' not in kwargs:
                kwargs['headers'] = self.headers
            else:
                kwargs['headers'].update(self.headers)
        if self.cookies:
            if 'cookies' not in kwargs:
                kwargs['cookies'] = self.cookies
            else:
                kwargs['cookies'].update(self.cookies)
        if 'proxy' not in kwargs and self.proxy:
            kwargs['proxy'] = self.proxy
        fail = 1
        while fail < 4:
            try:
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = timeout
                return await self._session.request(*args, **kwargs)
            except asyncio.exceptions.TimeoutError:
                fail += 1
                kwargs['timeout'] = aiohttp.ClientTimeout(total=self.timeout * fail)

    async def get(self, *args, **kwargs):
        if args:
            url = args[0]
            args = (f'{self.base_url}{url}', *args[1:])
        if 'url' in kwargs:
            url = kwargs['url']
            kwargs['url'] = f'{self.base_url}{url}'

        return await self.request('get', *args, **kwargs)

    async def post(self, *args, **kwargs):
        if args:
            url = args[0]
            args = (f'{self.base_url}{url}', *args[1:])
        if 'url' in kwargs:
            url = kwargs['url']
            kwargs['url'] = f'{self.base_url}{url}'
        return await self.request('post', *args, **kwargs)

    async def put(self, *args, **kwargs):
        if args:
            url = args[0]
            args = (f'{self.base_url}{url}', *args[1:])
        if 'url' in kwargs:
            url = kwargs['url']
            kwargs['url'] = f'{self.base_url}{url}'
        return await self.request('put', *args, **kwargs)

    async def delete(self, *args, **kwargs):
        if args:
            url = args[0]
            args = (f'{self.base_url}{url}', *args[1:])
        if 'url' in kwargs:
            url = kwargs['url']
            kwargs['url'] = f'{self.base_url}{url}'
        return await self.request('delete', *args, **kwargs)

    def _shutdown(self):
        try:
            asyncio.run(self._session.close())
        except Exception as e:
            return
