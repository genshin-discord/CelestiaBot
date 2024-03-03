import json
import re
import shutil

import svn.remote
import tempfile
import os
from git import Repo
from modules.apibase import *


class GenshinAPIBackend(APIBase):
    base_url = 'https://genshin.jmp.blue/'

    async def request(self, *args, **kwargs):
        r = await super().request(*args, **kwargs)
        if r:
            return await r.json()
        else:
            return []

    async def characters(self):
        return await self.get('characters')

    async def character(self, name):
        return await self.get(f'characters/{name}')


class GenshinDataBackend:
    def __init__(self):
        self.char_path = self.path = tempfile.mkdtemp()
        Repo.clone_from("https://github.com/genshindev/api.git", self.path, multi_options=['--depth=1'])
        self.char_path += '/assets/data/characters'

    @classmethod
    async def create(cls):
        return cls()

    def characters(self):
        result = []
        for _ in os.scandir(self.char_path):
            if _.is_dir() and _.name[0] != '.':
                result.append(_.name)
        return result

    def character(self, name):
        full_path = os.path.join(self.char_path, name)
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

    def __init__(self, backend: GenshinAPIBackend):
        self.backend = backend

    @classmethod
    async def create(cls):
        backend = await GenshinAPIBackend()
        c = cls(backend)
        await c.load()
        # backend.close()
        # await backend.close()
        return c

    async def load(self):
        for char in await self.backend.characters():
            self.data[char] = await self.backend.character(char)

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
