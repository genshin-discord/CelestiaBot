import re
import globals
from db import Abyss

description = 'Each character can only equip 4 artifacts'


async def fun_abyss_check(abyss: Abyss) -> bool:
    if not abyss.info:
        return False
    for team in abyss.info:
        for char in team:
            artifact = char[6]
            if len(artifact) > 4:
                return False
    return True
