import re
import globals
from db import Abyss

description = '12 battle counts only'


async def fun_abyss_check(abyss: Abyss) -> bool:
    if abyss.battle_count != 12:
        return False
    return True
