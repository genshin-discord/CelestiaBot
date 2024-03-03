import re
import globals
from db import Abyss

description = '4 star weapons only'


async def fun_abyss_check(abyss: Abyss) -> bool:
    if not abyss.info:
        return False
    for team in abyss.info:
        for char in team:
            weapon = char[5]
            if weapon[2] > 4:
                return False
    return True
