import os
import random

from db import *
import genshin
import globals
from constant import *
import importlib
from modules.genshin_data import GenshinData
from modules.log import log


async def abyss_update_user(client: genshin.Client, uid, gid, sess=db_sess):
    try:
        log.info(f'Updating abyss info for {uid}')
        genshin_abyss = await client.get_genshin_spiral_abyss(uid)
        star = 0
        if genshin_abyss.floors:
            last_floor = genshin_abyss.floors[-1]
            if last_floor.floor == 12 and last_floor.stars == 9:
                time_used = last_floor.chambers[-1].battles[-1].timestamp - last_floor.chambers[0].battles[0].timestamp
                time_used = time_used.total_seconds()
                if time_used > 0:
                    info = []
                    teams = ''
                    battle_teams = []
                    genshin_characters = await client.get_genshin_characters(uid)
                    char_map = {}
                    for c in genshin_characters:
                        char_map[c.id] = c
                    for battle in last_floor.chambers[0].battles:
                        team_used = []
                        team_info = []
                        for character in battle.characters:
                            name = character.name
                            if name in name_map:
                                name = name_map[name]

                            if character.id in char_map:
                                char_info = char_map[character.id]
                                if char_info.rarity == 5 and character.id not in [10000005, 10000007]:
                                    star += char_info.constellation + 1
                                if char_info.weapon.rarity == 5:
                                    star += char_info.weapon.refinement
                                team_used.append(f'{name}[C{char_info.constellation}]({character.level})')
                                team_info.append([name,
                                                  char_info.rarity,
                                                  char_info.constellation,
                                                  char_info.level,
                                                  char_info.element,
                                                  [char_info.weapon.name,
                                                   char_info.weapon.id,
                                                   char_info.weapon.rarity,
                                                   char_info.weapon.refinement,
                                                   char_info.weapon.level,
                                                   char_info.weapon.ascension],
                                                  [[x.level, x.rarity, x.set.id, x.set.name] for x in
                                                   char_info.artifacts],
                                                  char_info.id])
                        info.append(team_info)
                        battle_teams.append('/'.join(team_used))
                    if len(battle_teams) < 2:
                        log.warning(f'uid {uid} has single abyss team {battle_teams}')
                        return
                    teams += "\n".join(battle_teams)
                    teams = teams.strip()
                    log.info(f'Update {uid} time {time_used} {teams}')
                    battle_count = genshin_abyss.total_battles
                    await create_update_abyss(uid, genshin_abyss.season, time_used, teams, star, battle_count, gid,
                                              info,
                                              sess=sess)
    except genshin.errors.GenshinException as e:
        log.warning(f'Abyss update error {e} for {uid}')
        return


async def abyss_fun_module(season, sess=None):
    module_name = await get_abyss_fun_module(season, sess)
    if not module_name:
        total = ["3star_weapon", "4star_only", "fontaine_only", "mondstadt_only", "no_healers", "same_gender",
                 "same_weapon", "standard_only", "twelve_only", "4artifacts_only", "4star_weapon",
                 "inazuma_only", "liyue_only", "no_archons", "no_shield", "same_vision", "solo", "sumeru_only"]
        module_name = random.choice(total)
        await update_abyss_fun_module(season, module_name, sess)
    else:
        module_name = module_name.fun_module
    abyss_module = importlib.import_module(f'modules.abyss_fun.{module_name}')
    abyss_module = importlib.reload(abyss_module)
    return abyss_module


async def fun_abyss_filter(guild=None, limit=10, sess=None):
    if not globals.global_genshin_data:
        globals.global_genshin_data = await GenshinData.create()
    result = {}
    abyss_module = None
    for abyss in await get_current_season_full_abyss(guild=guild, sess=sess):
        abyss = abyss[0]
        if not abyss_module:
            abyss_module = await abyss_fun_module(abyss.season, sess)

        if await abyss_module.fun_abyss_check(abyss):
            if abyss.uid in result:
                if result[abyss.uid].time > abyss.time:
                    result[abyss.uid] = abyss
            else:
                result[abyss.uid] = abyss
    final = []
    total = 0
    for _, x in sorted(result.items(), key=lambda a: a[1].time):
        if total >= limit:
            break
        final.append(x)
        total += 1
    return final
