from modules.apibase import APIBase
from bs4 import BeautifulSoup
import re

code_regex = re.compile(r'^\w{6,16}$')
bad_codes = ['Giveaways']


class Codes(APIBase):
    base_url = 'https://www.pockettactics.com'

    async def list(self):
        try:
            data = await self.get('/genshin-impact/codes')
            b = BeautifulSoup(await data.text(), 'lxml')
            content = b.find('div', {'id': 'site_wrap'})
            codes = []
            for l in content.find_all('ul'):
                for code in l.find_all_next('strong'):
                    code = code.text.strip()
                    if code_regex.match(code) and code not in bad_codes:
                        codes.append(code)
            return list(set(codes))
        except Exception as e:
            print(f'Codes exception {e}')
            return []


# async def test():
#     c = await Codes.create()
#     print(await c.get())
#     await c.close()

# import asyncio
# asyncio.run(test())
