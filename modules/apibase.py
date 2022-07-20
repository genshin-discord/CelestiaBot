import asyncio

import aiohttp


class APIBase:
    base_url = ''
    headers = {'User-Agent': 'Mozilla/5.0'}
    cookies = None
    timeout = 5

    def __init__(self, s, base):
        self.s: aiohttp.ClientSession = s
        self.base_url = base

    @classmethod
    async def create(cls, base):
        timeout = aiohttp.ClientTimeout(total=cls.timeout)
        s = aiohttp.ClientSession(timeout=timeout)
        return cls(s, base)

    async def send(self, *args, **kwargs):
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
        fail = 1
        while fail < 4:
            try:
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = timeout
                result = await self.s.request(*args, **kwargs)
                return result
            except asyncio.exceptions.TimeoutError:
                fail += 1
                timeout = aiohttp.ClientTimeout(total=self.timeout * fail)
        return None

    async def get(self, *args, **kwargs):
        if args:
            url = args[0]
            args = (f'{self.base_url}{url}', *args[1:])
        if 'url' in kwargs:
            url = kwargs['url']
            kwargs['url'] = f'{self.base_url}{url}'

        return await self.send('get', *args, **kwargs)

    async def post(self, *args, **kwargs):
        if args:
            url = args[0]
            args = (f'{self.base_url}{url}', *args[1:])
        if 'url' in kwargs:
            url = kwargs['url']
            kwargs['url'] = f'{self.base_url}{url}'
        return await self.send('post', *args, **kwargs)

    async def put(self, *args, **kwargs):
        if args:
            url = args[0]
            args = (f'{self.base_url}{url}', *args[1:])
        if 'url' in kwargs:
            url = kwargs['url']
            kwargs['url'] = f'{self.base_url}{url}'
        return await self.send('put', *args, **kwargs)

    async def delete(self, *args, **kwargs):
        if args:
            url = args[0]
            args = (f'{self.base_url}{url}', *args[1:])
        if 'url' in kwargs:
            url = kwargs['url']
            kwargs['url'] = f'{self.base_url}{url}'
        return await self.send('delete', *args, **kwargs)

    async def close(self):
        await self.s.close()
