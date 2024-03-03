import re
import globals
from db import Abyss

description = 'Solo every chambers'


async def fun_abyss_check(abyss: Abyss) -> bool:
    count = 0
    for team in abyss.info:
        count += len(team)
    if count == 2:
        return True
    else:
        return False
