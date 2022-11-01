from modules.apibase import APIBase
import random

UA_LIST = []


async def random_ua():
    global UA_LIST
    if not UA_LIST:
        a = await APIBase.create('https://raw.githubusercontent.com/')
        r = await a.get('sqlmapproject/sqlmap/master/data/txt/user-agents.txt')
        data = await r.text()
        await a.close()
        for line in data.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                UA_LIST.append(line)
    return random.choice(UA_LIST)


# async def test():
#     print(await random_ua())
#
#
# import asyncio
# asyncio.run(test())