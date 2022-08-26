from db import *
import genshin
from constant import *
from modules.log import log


async def abyss_update_user(client: genshin.Client, uid, gid, sess=db_sess):
    try:
        log.info(f'Updating abyss info for {uid}')
        genshin_characters = await client.get_genshin_characters(uid)
        char_map = {}
        for c in genshin_characters:
            char_map[c.id] = c
        genshin_abyss = await client.get_genshin_spiral_abyss(uid)
        star = 0
        if genshin_abyss.floors:
            last_floor = genshin_abyss.floors[-1]
            if last_floor.floor == 12 and last_floor.stars == 9:
                time_used = last_floor.chambers[-1].battles[-1].timestamp - last_floor.chambers[0].battles[0].timestamp
                time_used = time_used.total_seconds()
                if time_used > 0:
                    teams = ''
                    battle_teams = []
                    for battle in last_floor.chambers[0].battles:
                        team_used = []
                        for character in battle.characters:
                            name = character.name
                            if name in name_map:
                                name = name_map[name]
                            team_used.append(f'{name}({character.level})')
                            if character.id in char_map:
                                if char_map[character.id].rarity == 5:
                                    star += char_map[character.id].constellation + 1
                                if char_map[character.id].weapon.rarity == 5:
                                    star += char_map[character.id].weapon.refinement
                        battle_teams.append('/'.join(team_used))
                    teams += "\n".join(battle_teams)
                    teams = teams.strip()
                    log.info(f'Update {uid} time {time_used} {teams}')
                    battle_count = genshin_abyss.total_battles
                    await create_update_abyss(uid, genshin_abyss.season, time_used, teams, star, battle_count, gid,
                                              sess=sess)
    except genshin.errors.GenshinException as e:
        log.warning(f'Abyss update error {e} for {uid}')
        return
