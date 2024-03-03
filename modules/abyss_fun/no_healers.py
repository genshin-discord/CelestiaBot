import re
import globals
from db import Abyss

description = 'No healers'


async def fun_abyss_check(abyss: Abyss) -> bool:
    healers = ['Baizhu', 'Jean', 'Kokomi', 'Qiqi', 'Barbara', 'Bennett', 'Diona', 'Dori', 'Mika', 'Noelle', 'Sayu',
               'Shinobu', 'Yaoyao', 'Xianyun']
    for heal_unit in healers:
        if heal_unit.lower() in abyss.team.lower():
            return False
    if 'gorou' in abyss.team.lower():
        for team in abyss.info:
            for char in team:
                if char[0].lower() == 'gorou' and char[2] > 3:
                    return False
    if 'zhongli' in abyss.team.lower():
        for team in abyss.info:
            for char in team:
                if char[0].lower() == 'zhongli' and char[2] > 5:
                    return False
    return True
