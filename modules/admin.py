import asyncio
import os

import aiohttp
import aiofiles
import genshin
from db import *
from constant import name_map
from modules.simsimi import AIChat
import discord
import datetime
from modules.daily import do_daily_user
from modules.tts import TTS
from typing import List
from tempfile import mktemp


async def download_temp(url: str):
    ext = url[url.rindex('.'):]
    local = mktemp(ext)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(local, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return local


async def do_reply(bot: discord.Bot, message: discord.Message):
    data = message.content.split(':', 3)
    op, channel, msg_id, text = data
    channel = int(channel)
    msg_id = int(msg_id)
    channel = await bot.fetch_channel(channel)
    msg = await channel.fetch_message(msg_id)

    if not text:
        text = None
    files = []
    for att in message.attachments:
        temp_path = await download_temp(att.url)
        if os.path.exists(temp_path):
            files.append(temp_path)
    if files:
        await msg.reply(text, files=[discord.File(x) for x in files])
    else:
        await msg.reply(text)
    await message.reply('Message sent')
    for x in files:
        try:
            os.unlink(x)
        except OSError as e:
            print(f'Remove {x} error {e}')


async def do_emoji(bot: discord.Bot, message: discord.Message):
    data = message.content.split(':', 3)
    op, channel, msg_id, emoji = data
    channel = int(channel)
    msg_id = int(msg_id)
    channel = await bot.fetch_channel(channel)
    msg = await channel.fetch_message(msg_id)
    await msg.add_reaction(emoji)
    return await message.reply('Emoji sent')


async def do_flash_emoji(bot: discord.Bot, message: discord.Message):
    data = message.content.split(':', 4)
    op, channel, msg_id, emoji, times = data
    channel = int(channel)
    msg_id = int(msg_id)
    times = int(times)
    if times > 50 or times < 0:
        times = 50
    channel = await bot.fetch_channel(channel)
    msg = await channel.fetch_message(msg_id)
    for x in range(times):
        await msg.add_reaction(emoji)
        await asyncio.sleep(0.5)
        await msg.remove_reaction(emoji, bot.user)
    return await message.reply('Emoji flash sent')


async def do_flash_emoji_history(bot: discord.Bot, message: discord.Message):
    data = message.content.split(':', 4)
    op, channel, msg_id, emoji, limit = data
    channel = int(channel)
    msg_id = int(msg_id)
    limit = int(limit)
    channel = await bot.fetch_channel(channel)
    msg = await channel.fetch_message(msg_id)
    msg_lists = []
    async for m in channel.history(limit=limit, before=msg):
        await m.add_reaction(emoji)
        msg_lists.append(m)

    for m in msg_lists:
        await m.remove_reaction(emoji, bot.user)

    return await message.reply('Emoji flash history sent')


async def do_send(bot: discord.Bot, message: discord.Message):
    data = message.content.split(':', 2)
    op, channel, text = data
    channel = int(channel)
    channel = await bot.fetch_channel(channel)
    if not text:
        text = None
    files = []
    for att in message.attachments:
        temp_path = await download_temp(att.url)
        if os.path.exists(temp_path):
            files.append(temp_path)
    if files:
        await channel.send(text, files=[discord.File(x) for x in files])
    else:
        await channel.send(text)
    await message.reply('Message sent')
    for x in files:
        try:
            os.unlink(x)
        except OSError as e:
            print(f'Remove {x} error {e}')


async def do_list(bot: discord.Bot, message: discord.Message):
    op, limit = message.content.split(':', 1)
    limit = int(limit)
    data = ''
    async for guild in bot.fetch_guilds(limit=limit):
        data += f'{guild.id} {guild.name}\n'
    return await message.reply(data)


async def do_daily(bot: discord.Bot, message: discord.Message):
    op, uid = message.content.split(':', 1)
    sess = await create_session()
    user = await fetch_user(uid, sess)
    await close_session(sess)
    try:
        reward = await do_daily_user(user, True)
        data = f'Daily done {user.nickname}[{user.uid}]'
    except Exception as e:
        data = f'Daily exception {str(e).strip()}'

    return await message.reply(data)


async def do_info(bot: discord.Bot, message: discord.Message):
    op, uid = message.content.split(':', 1)
    sess = await create_session()
    user = await fetch_user(uid, sess)
    await close_session(sess)
    try:
        data = ''
        cookie = json.loads(user.cookie)
        client = genshin.Client()
        client.set_cookies(cookie)
        client.default_game = genshin.Game.GENSHIN
        client.region = genshin.utility.recognize_region(user.uid, genshin.Game.GENSHIN)
        client.uid = user.uid
        gc = await client.get_genshin_characters(user.uid)
        for character in gc:
            data += f'{character.name}[{character.rarity}*] c{character.constellation} {character.weapon.name}[{character.weapon.rarity}*] r{character.weapon.refinement}\n'
        await close_session(sess)
    except Exception as e:
        data = f'Daily exception {str(e).strip()}'

    return await message.reply(data)


VOICE_CLIENT: List[discord.VoiceClient] = []


async def do_voice(bot: discord.Bot, message: discord.Message):
    global VOICE_CLIENT
    data = message.content.split(':', 1)
    op, channel = data
    channel = int(channel)
    channel = await bot.fetch_channel(channel)
    if isinstance(channel, discord.VoiceChannel):
        client = await channel.connect()
        VOICE_CLIENT.append(client)
        return await message.reply(f'Channel join, id={len(VOICE_CLIENT) - 1}')
    else:
        return await message.reply('Channel error')


async def do_voice_disconnect(bot: discord.Bot, message: discord.Message):
    global VOICE_CLIENT
    data = message.content.split(':', 1)
    op, channel = data
    channel = int(channel)
    if channel < len(VOICE_CLIENT):
        client = VOICE_CLIENT.pop(channel)
        await client.disconnect(force=True)
        return await message.reply(f'Channel {channel} disconnected')
    else:
        return await message.reply('Channel error')


async def do_voice_disconnect_all(bot: discord.Bot, message: discord.Message):
    global VOICE_CLIENT
    for vc in VOICE_CLIENT:
        await vc.disconnect(force=True)
    VOICE_CLIENT = []
    return await message.reply('All voice channel disconnected')


async def do_voice_list(bot: discord.Bot, message: discord.Message):
    global VOICE_CLIENT
    if len(VOICE_CLIENT):
        data = ''
        for idx, vc in enumerate(VOICE_CLIENT):
            channel = vc.channel
            guild = vc.guild
            data += f'{idx}. {guild.name} {channel.name} {vc.average_latency:0.2f}\n'
        return await message.reply(data)
    else:
        return await message.reply('No voice channel connected')


async def do_voice_speak(bot: discord.Bot, message: discord.Message):
    global VOICE_CLIENT
    data = message.content.split(':', 2)
    op, channel, text = data
    channel = int(channel)
    if channel < len(VOICE_CLIENT):
        vc = VOICE_CLIENT[channel]
        t = await TTS.create()
        b = await t.speak(text)
        tmp_voice = mktemp('.mp3')
        with open(tmp_voice, 'wb') as f:
            f.write(b.read())
        vc.play(discord.FFmpegPCMAudio(tmp_voice), after=lambda e: os.unlink(tmp_voice))
        return await message.reply(f'Voice sent')
    else:
        return await message.reply('Channel error')


async def do_voice_play(bot: discord.Bot, message: discord.Message):
    global VOICE_CLIENT
    data = message.content.split(':', 1)
    op, channel = data
    channel = int(channel)
    if channel < len(VOICE_CLIENT):
        vc = VOICE_CLIENT[channel]
        for att in message.attachments:
            tmp_voice = await download_temp(att.url)
            if os.path.exists(tmp_voice):
                vc.play(discord.FFmpegPCMAudio(tmp_voice), after=lambda e: os.unlink(tmp_voice))
        return await message.reply(f'Voice sent')
    else:
        return await message.reply('Channel error')


async def do_abyss(bot: discord.Bot, message: discord.Message):
    data = message.content.split(':', 1)
    op, uid = data
    sess = await create_session()
    user = await fetch_user(uid, sess)
    if not user:
        return await message.reply('No such uid')
    if not user.enabled:
        return await message.reply('User disabled')
    if not user.cookie:
        return await message.reply('User no cookie')

    cookie = json.loads(user.cookie)
    client = genshin.Client()
    client.set_cookies(cookie)
    client.region = genshin.utility.recognize_region(user.uid, genshin.Game.GENSHIN)
    client.lang = 'en-us'
    old_abyss = await fetch_user_abyss(uid, sess=sess)
    if old_abyss:
        result = 'Old data:\n' \
                 f'Season: {old_abyss.season}\n' \
                 f'5* count: {old_abyss.star}\n' \
                 f'Time: {old_abyss.time}\n' \
                 f'Teams: {old_abyss.team}\n' \
                 f'{"=" * 20}\n\n'
    else:
        result = ''
    genshin_abyss = await client.get_genshin_spiral_abyss(uid)
    result += f'Season: {genshin_abyss.season}\n'
    if genshin_abyss.floors:
        last_floor = genshin_abyss.floors[-1]
        result += f'Last floor: {genshin_abyss.max_floor}\n' \
                  f'Last floor stars: {last_floor.stars}\n\n'
        if last_floor.floor == 12 and last_floor.stars == 9:
            genshin_characters = await client.get_genshin_characters(uid)
            char_map = {}
            for c in genshin_characters:
                char_map[c.id] = c
            star = 0
            teams = ''
            for chamber in last_floor.chambers:
                star = 0
                result += f'Chamber: 12-{chamber.chamber} [{chamber.stars}/{chamber.max_stars}]\n'
                battle_teams = []
                for battle in chamber.battles:
                    team_used = []
                    for character in battle.characters:
                        name = character.name
                        if name in name_map:
                            name = name_map[name]
                        team_used.append(f'{name}({character.level})')
                        if character.id in char_map:
                            if char_map[character.id].rarity == 5 and character.id != 10000007:
                                star += char_map[character.id].constellation + 1
                            if char_map[character.id].weapon.rarity == 5:
                                star += char_map[character.id].weapon.refinement
                    battle_teams.append('/'.join(team_used))
                    result += f'Timestamp: {str(battle.timestamp)}\n'
                teams = "\n".join(battle_teams)
                teams = teams.strip()
                result += f'Star: {star}\n' \
                          f'Team: {teams}\n\n'

            time_used = last_floor.chambers[-1].battles[-1].timestamp - last_floor.chambers[0].battles[0].timestamp
            time_used = time_used.total_seconds()
            result += f'Total time: {time_used}s\n'
            if time_used > 0 and teams:
                await create_update_abyss(uid, genshin_abyss.season, time_used, teams, star,
                                          genshin_abyss.total_battles, user.discord_guild, sess)
    return await message.reply(result)


def channel_type(channel: discord.channel):
    if isinstance(channel, discord.TextChannel):
        return 'Text'
    elif isinstance(channel, discord.VoiceChannel):
        return 'Voice'
    elif isinstance(channel, discord.StageChannel):
        return 'Stage'
    elif isinstance(channel, discord.CategoryChannel):
        return 'Category'
    elif isinstance(channel, discord.ForumChannel):
        return 'Forum'
    else:
        return 'Unknown'


async def do_ls(bot: discord.Bot, message: discord.Message):
    op, server = message.content.split(':', 1)
    server = int(server)
    guild = await bot.fetch_guild(server)
    data = f'{guild.id} {guild.name}:\n' \
           f'Members: {guild.approximate_member_count}\n' \
           f'Created at: {str(guild.created_at)}\n'
    owner = await guild.fetch_member(guild.owner_id)
    data += f'Owner: {owner.name}#{owner.discriminator}[{owner.id}]\n'
    try:
        widget = await guild.widget()
        data += f'Invite url: {widget.invite_url}\n'
    except discord.Forbidden:
        pass
    except discord.HTTPException:
        pass
    data += '=' * 20 + '\n'
    for channel in await guild.fetch_channels():
        data += f'{channel.id} {channel.name}[{channel_type(channel)}]\n'
    for x in range(0, len(data), 2000):
        await message.channel.send(data[x:x + 2000])
    return


async def do_view(bot: discord.Bot, message: discord.Message):
    data = message.content.split(':')[1:]
    limit = 20
    before = datetime.datetime.now()
    if len(data) > 2:
        channel_id, limit, before = data
        limit = int(limit)
        before = datetime.datetime.fromtimestamp(int(before))
    elif len(data) > 1:
        channel_id, limit = data
        limit = int(limit)
    else:
        channel_id = data
    channel_id = int(channel_id)
    channel = await bot.fetch_channel(channel_id)
    content = ''
    async for msg in channel.history(limit=limit, before=before):
        content += f'{"=" * 20}\n' \
                   f'**{msg.author} {msg.created_at}[{msg.created_at.timestamp()}]**\n' \
                   f'{msg.content}\n'
    for x in range(0, len(content), 2000):
        await message.channel.send(content[x:x + 2000])
    return


async def do_nick(bot: discord.Bot, message: discord.Message):
    op, server, nick = message.content.split(':', 2)
    server = int(server)
    guild = await bot.fetch_guild(server)
    nick = nick.strip()
    if not nick:
        nick = None
    self = await guild.fetch_member(BOT_ID)
    await self.edit(nick=nick)
    return await message.reply('Nickname changed')


async def do_forum_create(bot: discord.Bot, message: discord.Message):
    op, channel, title, content = message.content.split(':', 3)
    channel = await bot.fetch_channel(int(channel))
    if isinstance(channel, discord.ForumChannel):
        await channel.create_thread(title, content)
        return await message.reply('Thread created')
    else:
        return await message.reply('Not forum channel')


async def do_forum_send(bot: discord.Bot, message: discord.Message):
    op, channel, tid, content = message.content.split(':', 3)
    channel = await bot.fetch_channel(int(channel))
    if isinstance(channel, discord.ForumChannel):
        thread = channel.get_thread(int(tid))
        if thread:
            await thread.send(content)
            return await message.reply('Message sent')
        return await message.reply('No such thread')
    else:
        return await message.reply('Not forum channel')


op_list = {'reply': [0, do_reply],
           'send': [0, do_send],
           'emoji': [0, do_emoji],
           'fe': [0, do_flash_emoji],
           'feh': [0, do_flash_emoji_history],
           'vc': [0, do_voice],
           'vcl': [0, do_voice_list],
           'vcd': [0, do_voice_disconnect],
           'vcda': [0, do_voice_disconnect_all],
           'vcs': [0, do_voice_speak],
           'vcp': [0, do_voice_play],
           'fc': [0, do_forum_create],
           'fs': [0, do_forum_send],
           'list': [1, do_list],
           'ls': [1, do_ls],
           'view': [1, do_view],
           'daily': [2, do_daily],
           'info': [2, do_info],
           'nick': [2, do_nick],
           'abyss': [2, do_abyss]
           }


async def dispatch_command(bot, op, message, admin: Admin):
    if op in op_list and admin.level > op_list[op][0]:
        try:
            return await op_list[op][1](bot, message)
        except Exception as e:
            error = f'Error in command dispatch {e}'
            print(error)
            await message.reply(error)
            return False
    else:
        return False


async def control_center(bot: discord.Bot, message: discord.Message):
    content = message.content
    admin = await get_admin(str(message.author.id))
    if admin and admin.level > 0:
        if ':' in content:
            op, data = content.split(':', 1)
            return await dispatch_command(bot, op, message, admin)
        else:
            return await AIChat(message, content)
    else:
        return await message.reply('You do not have bot chatting permission')
