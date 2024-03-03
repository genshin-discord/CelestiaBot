import re
import globals
from db import Abyss

description = 'Standard 5 stars only'


async def fun_abyss_check(abyss: Abyss) -> bool:
    standard = ['Qiqi', 'Diluc', 'Mona', 'Keqing', 'Jean', 'Tighnari', 'Dehya']
    for team in abyss.info:
        for char in team:
            if char[1] == 5 and char[0] not in standard:
                return False
    return True
