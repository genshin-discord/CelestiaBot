from modules.apibase import APIBase
from bs4 import BeautifulSoup
import re

code_regex = re.compile(r'^\w{6,16}$')


class Codes:
    def __init__(self, s):
        self.s: APIBase = s

    @classmethod
    async def create(cls):
        s = await APIBase.create('https://www.pockettactics.com')
        return cls(s)

    async def get(self):
        try:
            data = await self.s.get('/genshin-impact/codes')
            b = BeautifulSoup(await data.text(), 'lxml')
            content = b.find('div', {'id': 'site_wrap'})
            codes = []
            for l in content.find_all('ul'):
                for code in l.find_all_next('strong'):
                    code = code.text.strip()
                    if code_regex.match(code):
                        codes.append(code)
            return list(set(codes))
        except Exception as e:
            print(f'Codes exception {e}')
            return []

    async def close(self):
        await self.s.close()


async def test():
    c = await Codes.create()
    print(await c.get())
    await c.close()

# import asyncio
# asyncio.run(test())
