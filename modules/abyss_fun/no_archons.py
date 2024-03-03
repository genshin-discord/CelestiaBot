import re
import globals
from db import Abyss

description = 'No archons'


async def fun_abyss_check(abyss: Abyss) -> bool:
    archons = ['nahida', 'venti', 'zhongli', 'raiden', 'furina']
    for top_unit in archons:
        if top_unit in abyss.team.lower():
            return False
    return True
