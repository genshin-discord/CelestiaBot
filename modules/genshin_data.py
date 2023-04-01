import json
import re
import shutil

import svn.remote
import tempfile
import os


# from modules.apibase import *


class GenshinDataBackend:
    def __init__(self):
        self.path = tempfile.mkdtemp()
        r = svn.remote.RemoteClient('https://github.com/genshindev/api/trunk/assets/data/characters')
        r.checkout(self.path)

    @classmethod
    async def create(cls):
        return cls()

    def characters(self):
        result = []
        for _ in os.scandir(self.path):
            if _.is_dir() and _.name[0] != '.':
                result.append(_.name)
        return result

    def character(self, name):
        full_path = os.path.join(self.path, name)
        json_data = os.path.join(full_path, 'en.json')
        if os.path.exists(json_data):
            try:
                with open(json_data, 'r', encoding='utf-8', errors='ignore') as f:
                    return json.load(f)
            except UnicodeError as e:
                print(f'Error in loading {json_data}')
                return None
        # j = await self.s.get(f'characters/{name}')
        # return await j.json()

    def close(self):
        return shutil.rmtree(self.path, ignore_errors=True)


class GenshinData:
    data = {}

    def __init__(self, backend: GenshinDataBackend):
        self.backend = backend

    @classmethod
    async def create(cls):
        backend = await GenshinDataBackend.create()
        c = cls(backend)
        await c.load()
        backend.close()
        # await backend.close()
        return c

    async def load(self):
        for char in self.backend.characters():
            self.data[char] = self.backend.character(char)

    def __getitem__(self, item: str):
        item = item.lower()
        if item in self.data:
            return self.data[item]
        key_filter = re.compile(r'-|\s')
        item = key_filter.sub('', item)
        for k in self.data.keys():
            match_k = key_filter.sub('', k)
            if item in match_k or match_k in item:
                return self.data[k]


# async def test():
#     g = await GenshinData.create()
#     print(g['raiden'])
#     print(g['Kamisato Ayaka'])
#     print(g['Hu Tao'])
#
#
# import asyncio
#
# asyncio.run(test())
