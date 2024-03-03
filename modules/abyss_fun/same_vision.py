import re
import globals
from db import Abyss

description = 'Same vision each team'


async def fun_abyss_check(abyss: Abyss) -> bool:
    name_replace = re.compile(r'\(.+?\)')
    for team in abyss.team.split('\n'):
        team_vision = set()
        team_count = 0
        for char in team.split('/'):
            char = name_replace.sub('', char)
            if char.lower() == 'traveler':
                return False
            char_data = globals.global_genshin_data[char]
            if char_data and 'vision' in char_data:
                team_vision.add(char_data['vision'])
                team_count += 1
        if len(team_vision) != team_count:
            return False
    return True
