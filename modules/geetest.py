from modules.apibase import *
from time import time
from modules.useragent import random_ua
import json


class Geetest:

    def __init__(self, s):
        self.s: APIBase = s

    @classmethod
    async def create(cls):
        s = await APIBase.create('https://api.geevisit.com/')
        s.headers['User-Agent'] = await random_ua()
        s.headers.update({"Accept": "*/*",
                          "X-Requested-With": "com.mihoyo.hyperion",
                          "Referer": "https://webstatic.mihoyo.com/bbs/event/signin-ys/index.html?bbs_auth_required=true&act_id=e202009291139501&utm_source=bbs&utm_medium=mys&utm_campaign=icon",
                          "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
                          })
        return cls(s)

    async def crack(self, gt, challenge):
        try:
            fun = f'geetest_{int(time()) * 1000}'
            data = await self.s.get(
                f'ajax.php?gt={gt}&challenge={challenge}&lang=zh-cn&pt=0&client_type=web&callback={fun}')
            j = await data.text()
            if j.startswith(fun):
                j = j[len(fun) + 1:]
                j = j[:-1]
            j = json.loads(j)
            return j
        except Exception as e:
            print(f'Codes exception {e}')
            return []

    async def close(self):
        await self.s.close()
