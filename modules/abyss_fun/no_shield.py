import re
import globals
from db import Abyss

description = 'No shield characters'


async def fun_abyss_check(abyss: Abyss) -> bool:
    shield = ['kirara', 'zhongli', 'diona', 'noelle', 'beidou', 'xinyan', 'layla', 'baizhu']
    for shield_unit in shield:
        if shield_unit in abyss.team.lower():
            return False
    if 'yanfei' in abyss.team.lower():
        for team in abyss.info:
            for char in team:
                if char[0].lower() == 'yanfei' and char[2] > 3:
                    return False
    return True
