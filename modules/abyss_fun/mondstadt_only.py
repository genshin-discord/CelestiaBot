import re
import globals
from db import Abyss

description = 'Mondstadt characters only'


async def fun_abyss_check(abyss: Abyss) -> bool:
    name_replace = re.compile(r'\(.+?\)')
    for team in abyss.team.split('\n'):
        for char in team.split('/'):
            char = name_replace.sub('', char)
            char_data = globals.global_genshin_data[char]
            if char_data:
                if char_data['nation'] != 'Mondstadt':
                    return False
    return True
