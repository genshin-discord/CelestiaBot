from modules.apibase import APIBase
import random

UA_LIST = []


async def random_ua() -> str:
    # global UA_LIST
    # if not UA_LIST:
    #     a = await APIBase.create('https://raw.githubusercontent.com/')
    #     r = await a.get('sqlmapproject/sqlmap/master/data/txt/user-agents.txt')
    #     data = await r.text()
    #     await a.close()
    #     for line in data.split('\n'):
    #         line = line.strip()
    #         if line and not line.startswith('#'):
    #             UA_LIST.append(line)
    # return random.choice(UA_LIST)
    # well random useragent doesn't really work
    return 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/2.34.1'

# async def test():
#     print(await random_ua())
#
#
# import asyncio
# asyncio.run(test())