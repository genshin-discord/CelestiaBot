from db import *
import genshin
import discord
from modules.log import log
from typing import Dict


class Notify:
    resin: bool
    expeditions: bool
    realm: bool
    transformer: bool

    def clear(self):
        self.resin = self.expeditions = self.realm = self.transformer = False


global_notify: Dict[int, Notify] = {}


async def notify_user(bot: discord.Bot, user: User, content: str):
    try:
        discord_user = await bot.fetch_user(int(user.discord_id))
        if discord_user:
            await discord_user.send(content)
    except Exception as e:
        print(f'Notify user failed {e}')
        return


async def note_check_user(bot: discord.Bot, client: genshin.Client, user: User):
    global global_notify
    try:
        if not user.notify:
            return
        if user.uid not in global_notify:
            notify = Notify()
            notify.clear()
            global_notify[user.uid] = notify
        log.info(f'Note check for {user.uid}')
        note = await client.get_genshin_notes(user.uid)
        if note.remaining_resin_recovery_time is not None \
                and note.remaining_resin_recovery_time.total_seconds() < 3600:
            if not global_notify[user.uid].resin:
                global_notify[user.uid].resin = True
                content = f'{user.nickname}[{user.uid}], your resin will be maxed within {note.remaining_resin_recovery_time} ({note.current_resin}/{note.max_resin})'
                await notify_user(bot, user, content)
        else:
            global_notify[user.uid].resin = False

        if note.remaining_transformer_recovery_time is not None \
                and note.remaining_transformer_recovery_time.total_seconds() < 3600:
            if not global_notify[user.uid].transformer:
                global_notify[user.uid].transformer = True
                content = f'{user.nickname}[{user.uid}], your transformer will be available again within {note.remaining_transformer_recovery_time}'
                await notify_user(bot, user, content)
        else:
            global_notify[user.uid].transformer = False
        if note.remaining_realm_currency_recovery_time is not None \
                and note.remaining_realm_currency_recovery_time.total_seconds() < 3600:
            if not global_notify[user.uid].realm:
                global_notify[user.uid].realm = True
                content = f'{user.nickname}[{user.uid}], your realm currency will be maxed within {note.remaining_realm_currency_recovery_time}' \
                          f', current {note.current_realm_currency}/{note.max_realm_currency}'
                await notify_user(bot, user, content)
        else:
            global_notify[user.uid].realm = False

    except genshin.errors.GenshinException as e:
        log.warning(f'Note error {e} for {user.uid}')
        return
