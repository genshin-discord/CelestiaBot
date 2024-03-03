import re
import globals
from db import Abyss

description = 'Same gender each team'


async def fun_abyss_check(abyss: Abyss) -> bool:
    name_replace = re.compile(r'\(.+?\)')
    for team in abyss.team.split('\n'):
        team_gender = set()
        for char in team.split('/'):
            char = name_replace.sub('', char)
            char_data = globals.global_genshin_data[char]
            if char_data and 'gender' in char_data:
                team_gender.add(char_data['gender'])
        if len(team_gender) != 1:
            return False
    return True
