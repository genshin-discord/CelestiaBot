import re
import globals
from db import Abyss

description = '4 star characters only'


async def fun_abyss_check(abyss: Abyss) -> bool:
    if not abyss.info:
        return False
    for team in abyss.info:
        for char in team:
            if char[1] > 4:
                return False
    return True
