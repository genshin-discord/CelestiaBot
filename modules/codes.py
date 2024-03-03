from modules.apibase import APIBase
from bs4 import BeautifulSoup
import re

code_regex = re.compile(r'^\w{6,16}$')
bad_codes = ['Giveaways']


class Codes(APIBase):
    base_url = 'https://genshin-impact.fandom.com/'

    async def list(self):
        try:
            data = await self.get('wiki/Promotional_Code')
            b = BeautifulSoup(await data.text(), 'lxml')
            content = b.find('div', {'class': 'mw-parser-output'})
            table = content.find('table')
            tbody = table.find('tbody')
            codes = []

            for row in tbody.find_all('tr'):
                tds = row.find_all('td')
                if len(tds) > 3:
                    c = tds[0]
                    s = tds[1]
                    d = tds[2]
                    v = tds[3]
                    if 'background-color:rgb(255,153,153,0.5)' in v.attrs['style']:
                        break
                    reward = ''
                    for r in d.find_all('span', {'class': 'item'}):
                        reward += f'{r.text.strip()}\n'
                    for a in c.find_all('a'):
                        codes.append([a.text.strip(), reward.strip()])
            return codes
        except Exception as e:
            print(f'Codes exception {e}')
            return []


# async def test():
#     c = await Codes()
#     print(await c.list())
#
#
# import asyncio
#
# asyncio.run(test())
