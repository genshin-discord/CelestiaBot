from db import *
import genshin
import globals
from constant import *
import re
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
                            team_used.append(f'{name}({character.level})')
                            if character.id in char_map:
                                char_info = char_map[character.id]
                                if char_info.rarity == 5 and character.id not in [10000005, 10000007]:
                                    star += char_info.constellation + 1
                                if char_info.weapon.rarity == 5:
                                    star += char_info.weapon.refinement
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
                                                   char_info.artifacts]])
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


async def fun_abyss_check(abyss: Abyss) -> bool:
    name_replace = re.compile(r'\(.+?\)')
    for team in abyss.team.split('\n'):
        for char in team.split('/'):
            char = name_replace.sub('', char)
            if char.lower() == 'wanderer':
                continue
            char_data = globals.global_genshin_data[char]
            if char_data:
                if char_data['nation'] != 'Sumeru':
                    return False
    return True


async def fun_abyss_check_65(abyss: Abyss) -> bool:
    if abyss.battle_count != 12:
        return False
    return True


async def fun_abyss_check_64(abyss: Abyss) -> bool:
    name_replace = re.compile(r'\(.+?\)')
    for team in abyss.team.split('\n'):
        team_gender = set()
        for char in team.split('/'):
            char = name_replace.sub('', char)
            char_data = globals.global_genshin_data[char]
            if char_data and 'gender' in char_data:
                team_gender.add(char_data['weapon'])
        if len(team_gender) != 1:
            return False
    return True


async def fun_abyss_check_63(abyss: Abyss) -> bool:
    if not abyss.info:
        return False
    for team in abyss.info:
        for char in team:
            weapon = char[5]
            if weapon[2] > 4:
                return False
    return True


async def fun_abyss_check_62(abyss: Abyss) -> bool:
    if not abyss.info:
        return False
    for team in abyss.info:
        for char in team:
            weapon = char[5]
            if weapon[2] > 3:
                return False
    return True


async def fun_abyss_check_61(abyss: Abyss) -> bool:
    name_replace = re.compile(r'\(.+?\)')
    for team in abyss.team.split('\n'):
        team_gender = set()
        for char in team.split('/'):
            char = name_replace.sub('', char)
            char_data = globals.global_genshin_data[char]
            if char_data and 'gender' in char_data:
                team_gender.add(char_data['gender'])
        if len(team_gender) != 1:
            return False
    return True


async def fun_abyss_check_60(abyss: Abyss) -> bool:
    name_replace = re.compile(r'\(.+?\)')
    for team in abyss.team.split('\n'):
        for char in team.split('/'):
            char = name_replace.sub('', char)
            char_data = globals.global_genshin_data[char]
            if char_data:
                if char_data['nation'] != 'Inazuma':
                    return False
    return True


async def fun_abyss_filter(guild=None, limit=10, sess=None):
    if not globals.global_genshin_data:
        globals.global_genshin_data = await GenshinData.create()
    result = {}
    for abyss in await get_current_season_full_abyss(guild=guild, sess=sess):
        abyss = abyss[0]
        if await fun_abyss_check(abyss):
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
