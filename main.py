import asyncio
import datetime
import logging as log
import time
from http.cookies import SimpleCookie
from tempfile import mktemp
from typing import Dict
import discord
import enkapy
import genshin
import genshin.errors
from discord.ext import bridge, tasks, commands
from discord.commands import Option
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import MaxNLocator
import numpy as np
from constant import *
from db import *
from modules.artifact import EnkaArtifact
from modules.simsimi import SIMChatBot
from modules.codes import Codes
from modules.admin import control_center

log.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=log.INFO)
intents = discord.Intents.default()
intents.members = True
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
# bot = bridge.Bot(intents=intents, command_prefix='/', debug_guilds=TEST_GUILDS)

bot = bridge.Bot(intents=intents, command_prefix='/')


class RegModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            discord.ui.InputText(
                label="Your hoyoverse cookies",
                placeholder="Genshin hoyoverse cookie",
                style=discord.InputTextStyle.long,
            ),
            *args,
            **kwargs,
        )

    async def callback(self, interaction: discord.Interaction):
        cookie_str = self.children[0].value
        cookie_str = str(cookie_str).strip().strip('\'').strip('"')
        for _ in [';', 'ltuid', 'ltoken', 'cookie_token', 'account_id']:
            if _ not in cookie_str:
                log.warning(f'User {interaction.user.id} {interaction.user.name} sent {cookie_str}')
                return await interaction.response.send_message(f'Wrong cookies string![{_}]{COOKIE_HELP}')
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        cookies = {k: v.value for k, v in cookie.items()}

        for _ in ['ltuid', 'ltoken', 'cookie_token', 'account_id']:
            if _ not in cookies:
                log.warning(f'User {interaction.user.id} {interaction.user.name} sent {cookie_str}')
                return await interaction.response.send_message(f'Wrong cookies![{_}]{COOKIE_HELP}')

        client = genshin.Client()
        client.set_cookies(cookies)
        client.default_game = genshin.Game.GENSHIN

        try:
            client.region = genshin.Region.OVERSEAS
            accounts = await client.get_game_accounts()
        except genshin.errors.InvalidCookies:
            try:
                client.region = genshin.Region.CHINESE
                accounts = await client.get_game_accounts()
            except genshin.errors.InvalidCookies:
                return await interaction.response.send_message(f'Wrong cookies![Login failure]{COOKIE_HELP}')
        messages = ''
        sess = await create_session()
        for acc in accounts:
            if acc.game == genshin.Game.GENSHIN:
                uid = acc.uid
                level = acc.level
                nick = acc.nickname
                messages += f'Account {nick}[{uid}] added.\n'
                await create_update_user(uid, json.dumps(cookies), nick, level, interaction.user.id,
                                         interaction.guild_id, sess=sess)
                abyss = await get_abyss(uid, sess=sess)
                await update_user_artifact(uid, interaction.guild.id, sess=sess)
                if not abyss:
                    await abyss_update_user(client, uid, interaction.guild.id, sess=sess)
        await close_session(sess)
        if not messages:
            messages = 'No genshin account detected.'
        await interaction.response.send_message(messages)


@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="holy relics brushing"))
    log.info(f"{bot.user} Logged in")


global_chat_bot: SIMChatBot = None


@bot.event
async def on_message(message: discord.Message):
    global global_chat_bot
    if not global_chat_bot:
        global_chat_bot = await SIMChatBot.create()
    mentioned = False
    dm = False
    if message.mentions:
        for user in message.mentions:
            if user.id == BOT_ID:
                mentioned = True
                break
    if isinstance(message.channel, discord.DMChannel) and message.author.id != BOT_ID:
        dm = True
    if mentioned or dm:
        if not dm and message.guild and message.guild.id not in TEST_GUILDS:
            return await message.reply('Due to api limit, your server cannot use chatbot for now.')
        content = message.content.replace(f'<@{BOT_ID}>', '').strip()
        if dm:
            return await control_center(bot, message, global_chat_bot)
        if not message.author.bot:
            await message.reply(await global_chat_bot.chat(content))


@bot.bridge_command(name="global_abyss_rank", description="Show top 10 abyss record in all servers")
async def abyss_rank(ctx: discord.ApplicationContext):
    embed = discord.Embed(
        title="Global abyss rank",
        description="Only counts seconds between 12-3-2 and 12-1-1",
        color=discord.Color.random())
    cur = 1
    # embed.add_field(name=chr(173), value=chr(173))
    sess = await create_session()
    for abyss in await get_abyss_rank(None, 10, sess=sess):
        abyss = abyss[0]
        user = await fetch_user(abyss.uid, sess=sess)
        if user:
            uid = str(user.uid)
            uid = uid[:2] + '\\*' * (len(uid) - 3) + uid[-1:]
            embed.add_field(name=chr(173), value=f"**{cur}.{user.nickname} {uid} {abyss.time}s [{abyss.star}*]**\n"
                                                 f"{abyss.team}",
                            inline=False)
            cur += 1

    embed.set_footer(text="Only top 10 are shown.")
    await close_session(sess)
    await ctx.respond(embed=embed)


@bot.bridge_command(name="abyss_rank", description="Show top 5 abyss record in current server")
async def abyss_rank(ctx: discord.ApplicationContext):
    embed = discord.Embed(
        title="Abyss rank",
        description="Only counts seconds between 12-3-2 and 12-1-1",
        color=discord.Color.random())
    cur = 1
    sess = await create_session()
    for abyss in await get_abyss_rank(ctx.guild_id, sess=sess):
        abyss = abyss[0]
        user = await fetch_user(abyss.uid, sess=sess)
        if user:
            # embed.add_field(name=chr(173), value=chr(173))
            embed.add_field(name=chr(173), value=f"**{cur}.{user.nickname} {user.uid} {abyss.time}s [{abyss.star}*]**\n"
                                                 f"{abyss.team}",
                            inline=False)
            cur += 1

    embed.set_footer(text="Only top 5 in this server are shown.")
    await close_session(sess)
    await ctx.respond(embed=embed)


async def plot_artifact_rank(gid, sess):
    data = await artifact_count_rank(gid, sess)
    plt.rcdefaults()
    fig, ax = plt.subplots(figsize=(8, 4))

    users = []
    counts = []
    for uid, count in data:
        user = await fetch_user(uid, sess)
        users.append(user.nickname)
        counts.append(count)
    y_pos = np.arange(len(users))
    font = FontProperties(fname='/usr/share/fonts/truetype/arphic/ukai.ttc', size=12)
    plt.rcParams.update({'figure.autolayout': True})
    plt.style.use('fivethirtyeight')
    ax.barh(y_pos, counts, align='center')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_yticks(y_pos, labels=users, fontproperties=font)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Artifact counts')
    rects = ax.patches

    for rect, label in zip(rects, counts):
        ax.text(
            rect.get_x() + rect.get_width() - 0.4, rect.get_y() + rect.get_height() / 2,
            str(label),
            ha="center",
            va="center",
            fontproperties=font
        )
    tmp = mktemp('.png')
    fig.savefig(tmp, transparent=False, dpi=80, bbox_inches="tight")
    plt.close(fig)
    return tmp


@bot.bridge_command(name="artifact_rank", description="Show top 5 artifacts in current server")
async def artifact_rank(ctx: discord.ApplicationContext):
    embeds = []
    embed = discord.Embed(
        title="Artifact rank",
        description="Score = cr*2 + cd\nGoblet: HP%/ATK%/DEF% excluded.\nCirclet: Healing Bonus/HP%/ATK%/DEF% excluded."
                    "\n\nTop 5 good artifact(score>30) owner",
        color=discord.Color.random())
    embed.set_footer(text="Only top 5 in this server are shown.")
    embeds.append(embed)

    cur = 1
    sess = await create_session()
    png_plot = await plot_artifact_rank(ctx.guild_id, sess=sess)
    plot = discord.File(png_plot, filename="image.png")
    embed.set_image(url="attachment://image.png")
    await ctx.respond(embed=embeds[0], file=plot)

    for artifact in await get_artifact_rank(ctx.guild_id, sess=sess):
        artifact = artifact[0]
        user = await fetch_user(artifact.uid, sess)

        if user:
            embed = discord.Embed(
                title=f'{cur}. Score:{artifact.score}',
                description=f"{user.nickname} {user.uid}",
                color=discord.Color.random()
            )
            embed.set_thumbnail(url=artifact.icon_url)
            stats = json.loads(artifact.artifact)
            value = f'{stats["main"]["prop"]}\t{stats["main"]["value"]}\n\n'
            for sub in stats['sub']:
                value += f'*{sub["prop"]}\t{sub["value"]}*\n'
            embed.add_field(name=f"**{artifact.name}**", value=value, inline=False)
            embeds.append(embed)
            cur += 1
    await close_session(sess)

    for embed in embeds[1:]:
        await ctx.channel.send(embed=embed)


@bot.bridge_command(name="reg", description="Register your account via cookies")
async def reg(ctx: discord.ApplicationContext):
    modal = RegModal(title="Register your account")
    await ctx.send_modal(modal)


@bot.bridge_command(name="remove_me", description="Remove all your info")
async def remove_me(ctx: discord.ApplicationContext):
    sess = await create_session()
    await remove_user(ctx.user.id, ctx.guild.id, sess=sess)
    await close_session(sess)
    await ctx.respond('All your accounts are removed.')


@bot.bridge_command(name='notify', description="Change genshin related notifications")
async def notify_change(ctx: discord.ApplicationContext,
                        opt: Option(str, 'On or off', choices=["On", "Off"], required=True)):
    await ctx.defer()
    if not isinstance(opt, str):
        opt = str(opt)
    opt = opt.lower()
    if opt == 'on':
        t = 'enabled'
        opt = 1
    else:
        t = 'disabled'
        opt = 0
    sess = await create_session()
    users = await get_discord_users(ctx.user.id, ctx.guild.id, sess=sess)
    resp = 'Account not found, add account via /reg first!'
    if users:
        resp = ''
        for user in users:
            if user.enabled and user.cookie:
                user.notify = opt
                resp += f'Account {user.nickname}[{user.uid}] notification {t}.\n'
        sess.add_all(users)
        await sess.commit()
        if not resp:
            resp = 'Your accounts are disabled.'
    await close_session(sess)
    return await ctx.followup.send(resp)


@bot.bridge_command(name='codes', description="Retrieve all current available redeem codes")
async def codes(ctx: discord.ApplicationContext):
    await ctx.defer()
    c = await Codes.create()
    redeem_codes = await c.get()
    if redeem_codes:

        embed = discord.Embed(
            title=f'Total codes: {len(redeem_codes)}',
            description=f"Current redeemable codes",
            color=discord.Color.random()
        )
        #        embed.add_field(name=chr(173), value=chr(173))
        for cur, code in enumerate(redeem_codes):
            #            embed.add_field(name=chr(173), value=chr(173))
            embed.add_field(name=chr(173), value=f"**{cur + 1}.{code}**", inline=False)
            cur += 1
    else:
        embed = discord.Embed(
            title=f'No redeemable codes now',
            description=f"GG",
            color=discord.Color.random()
        )
    embed.set_footer(text="All codes are updated in real time.")
    return await ctx.followup.send(embed=embed)


@bot.bridge_command(name='redeem', description="Redeem code for your accounts")
async def redeem(ctx: discord.ApplicationContext, code: str):
    await ctx.defer()
    sess = await create_session()
    code = code.strip()
    users = await get_discord_users(ctx.user.id, ctx.guild.id, sess=sess)
    resp = 'Account not found, add account via /reg first!'
    if users:
        resp = ''
        for user in users:
            if user.enabled:
                cookie = json.loads(user.cookie)
                log.info(f'Trying to redeem code {code} for {user.uid}')

                client = genshin.Client()
                client.set_cookies(cookie)
                client.region = genshin.utility.recognize_region(user.uid, genshin.Game.GENSHIN)
                if client.region == genshin.Region.CHINESE:
                    resp += f'Redeem failed {user.nickname}[{user.uid}], CN server not supported\n'
                    continue
                client.default_game = genshin.Game.GENSHIN
                try:
                    await client.redeem_code(code, uid=user.uid)
                    resp += f'Redeem success {user.nickname}[{user.uid}]\n'
                    await asyncio.sleep(3)
                except genshin.errors.RedemptionClaimed:
                    resp += f'Redeem already claimed {user.nickname}[{user.uid}]\n'
                except genshin.errors.RedemptionInvalid:
                    resp = 'Code invalid'
                    break
                except genshin.errors.RedemptionCooldown:
                    await asyncio.sleep(3)
                    continue
                except genshin.errors.GenshinException as e:
                    resp += f'Redeem failed {user.nickname}[{user.uid}], cookies or code invalid\n'
                    print(e)
        if not resp:
            resp = 'Your accounts are disabled.'
    await close_session(sess)
    return await ctx.followup.send(resp)


@bot.bridge_command(name='profile', description="Get your profile data")
async def refresh(ctx: discord.ApplicationContext):
    await ctx.defer()
    embed = discord.Embed(
        title="Account profile",
        description="View your current profile in detail",
        color=discord.Color.random())
    sess = await create_session()
    users = await get_discord_users(ctx.user.id, ctx.guild.id, sess=sess)

    if users:
        for user in users:
            if user.enabled:
                abyss = await get_abyss(user.uid, sess)
                artifact_count = await get_user_artifact_count(user.discord_guild, user.uid, sess)
                if not abyss:
                    embed.add_field(name=chr(173),
                                    value=f"**{user.nickname} {user.uid}**\n"
                                          f"Good artifacts:{artifact_count}\n"
                                          "No abyss info, try max floor 12 first.",
                                    inline=False)
                    continue
                abyss_rank_server = await get_user_abyss_rank(user.discord_guild, user.uid, sess)
                abyss_rank_global = await get_user_abyss_rank(None, user.uid, sess)
                embed.add_field(name=chr(173),
                                value=f"**{user.nickname} {user.uid}**\n"
                                      f"Good artifacts: **{artifact_count}**\n"
                                      f"Abyss time: **{abyss.time}s**\n"
                                      f"Abyss rank(server): **{abyss_rank_server + 1}**\n"
                                      f"Abyss rank(global): **{abyss_rank_global + 1}**\n"
                                      f"Abyss battle count: **{abyss.battle_count}**\n"
                                      f"Abyss team stars: **{abyss.star}**\n"
                                      f"{abyss.team}",
                                inline=False)
                embed.set_footer(text='Battle count updates only if you get better records.')
        if not embed.fields:
            embed.add_field(name=chr(173), value='**Your accounts are disabled.**')
    else:
        embed.add_field(name=chr(173), value='**Account not found, add account via /reg first!**')
    await ctx.followup.send(embed=embed)


@bot.bridge_command(name='refresh', description="Refresh data for your accounts(once per 12 hour)")
async def refresh(ctx: discord.ApplicationContext):
    await ctx.defer()
    sess = await create_session()
    users = await get_discord_users(ctx.user.id, ctx.guild.id, sess=sess)
    resp = 'Account not found, add account via /reg first!'
    if users:
        resp = ''
        e = await EnkaArtifact.create()
        for user in users:
            if user.enabled and user.cookie:
                if not user.last_refresh:
                    user.last_refresh = 0
                if time.time() - user.last_refresh > 12 * 3600:
                    cookie = json.loads(user.cookie)
                    client = genshin.Client()
                    client.set_cookies(cookie)
                    client.region = genshin.utility.recognize_region(user.uid, genshin.Game.GENSHIN)
                    client.default_game = genshin.Game.GENSHIN
                    await abyss_update_user(client, user.uid, user.discord_guild, sess=sess)
                    await artifact_update_user(e, user.uid, user.discord_guild)
                    await update_refresh_time(user.uid, sess=sess)
                    resp += f'Account {user.nickname}[{user.uid}] refreshed.\n'
                else:
                    resp = 'You can only use /refresh once per 12 hours!'
        if not resp:
            resp = 'Your accounts are disabled.'
    await close_session(sess)
    return await ctx.followup.send(resp)


class SupremeHelpCommand(commands.HelpCommand):
    def get_command_signature(self, command):
        return '%s%s %s' % (self.context.clean_prefix, command.qualified_name, command.signature)

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help", color=discord.Color.blurple())
        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)
            if command_signatures := [
                self.get_command_signature(c) for c in filtered
            ]:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=self.get_command_signature(command), color=discord.Color.blurple())
        if command.help:
            embed.description = command.help
        if alias := command.aliases:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_help_embed(self, title, description, commands):  # a helper function to add commands to an embed
        embed = discord.Embed(title=title, description=description or "No help found...")

        if filtered_commands := await self.filter_commands(commands):
            for command in filtered_commands:
                embed.add_field(name=self.get_command_signature(command), value=command.help or "No help found...")

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        title = self.get_command_signature(group)
        await self.send_help_embed(title, group.help, group.commands)

    async def send_cog_help(self, cog):
        title = cog.qualified_name or "No"
        await self.send_help_embed(f'{title} Category', cog.description, cog.get_commands())


bot.help_command = SupremeHelpCommand()


@tasks.loop(hours=1)
async def do_daily():
    sess = await create_session()
    for user in await fetch_all_users(sess):
        user = user[0]
        if await check_daily_time(user.uid, sess):
            if user.enabled:
                retry, retry_times = 1, 0
                while retry and retry_times < 5:
                    cookie = json.loads(user.cookie)
                    log.info(f'Doing daily for {user.uid}')

                    client = genshin.Client()
                    client.set_cookies(cookie)
                    client.default_game = genshin.Game.GENSHIN
                    client.region = genshin.utility.recognize_region(user.uid, genshin.Game.GENSHIN)
                    client.uid = user.uid
                    retry = 0
                    try:
                        await client.claim_daily_reward(reward=False)
                        await update_daily_time(user.uid, sess)
                    except genshin.errors.AlreadyClaimed:
                        log.info(f'{user.uid} already claimed')
                    except genshin.errors.InvalidCookies:
                        discord_user = await bot.fetch_user(user.discord_id)
                        await discord_user.send(f'Account {user.nickname}[{user.uid}] session expired.{COOKIE_HELP}')
                        await disable_user_cookies(user.cookie, sess)
                    except genshin.errors.TooManyRequests:
                        log.warning(f'Retrying {user.uid}')
                        await asyncio.sleep(3)
                        retry = 1
                        retry_times += 1
                    except Exception as e:
                        if 'too many requests' in str(e).lower():
                            log.warning(f'Retrying {user.uid}')
                            await asyncio.sleep(3)
                            retry = 1
                            retry_times += 1
                        log.warning(f'Exception in daily {e}')
                    finally:
                        await asyncio.sleep(3)
                if retry_times >= 5:
                    log.warning(f'Too many retries! {user.nickname}[{user.uid}]')

    await close_session(sess)


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


class Notify:
    resin: bool
    expeditions: bool
    realm: bool
    transformer: bool

    def clear(self):
        self.resin = self.expeditions = self.realm = self.transformer = False


global_notify: Dict[int, Notify] = {}


async def notify_user(user: User, content: str):
    try:
        discord_user = await bot.fetch_user(int(user.discord_id))
        if discord_user:
            await discord_user.send(content)
    except Exception as e:
        print(f'Notify user failed {e}')
        return


async def note_check_user(client: genshin.Client, user: User):
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
                await notify_user(user, content)
        else:
            global_notify[user.uid].resin = False

        if note.remaining_transformer_recovery_time is not None \
                and note.remaining_transformer_recovery_time.total_seconds() < 3600:
            if not global_notify[user.uid].transformer:
                global_notify[user.uid].transformer = True
                content = f'{user.nickname}[{user.uid}], your transformer will be available again within {note.remaining_transformer_recovery_time}'
                await notify_user(user, content)
        else:
            global_notify[user.uid].transformer = False

        # if note.expeditions is not None:
        #     exp_time = {}
        #
        #     for expedition in note.expeditions:
        #         if expedition.remaining_time.total_seconds() < 3600:
        #             exp_time[expedition.character.name] = expedition.remaining_time
        #     if exp_time:
        #         if not global_notify[user.uid].expeditions:
        #             global_notify[user.uid].expeditions = True
        #             content = ''
        #             for name, remain_time in exp_time.items():
        #                 content += f'{user.nickname}[{user.uid}], your expedition {name} will be finished in {remain_time}\n'
        #             await notify_user(user, content)
        #     else:
        #         global_notify[user.uid].expeditions = False

        if note.remaining_realm_currency_recovery_time is not None \
                and note.remaining_realm_currency_recovery_time.total_seconds() < 3600:
            if not global_notify[user.uid].realm:
                global_notify[user.uid].realm = True
                content = f'{user.nickname}[{user.uid}], your realm currency will be maxed within {note.remaining_realm_currency_recovery_time}' \
                          f', current {note.current_realm_currency}/{note.max_realm_currency}'
                await notify_user(user, content)
        else:
            global_notify[user.uid].realm = False

    except genshin.errors.GenshinException as e:
        log.warning(f'Note error {e} for {user.uid}')
        return


@tasks.loop(hours=1)
async def data_update():
    """Update abyss and check user note"""
    sess = await create_session()
    for user in await fetch_all_users(sess):
        user = user[0]
        if user.cookie and user.enabled:
            cookie = json.loads(user.cookie)
            client = genshin.Client()
            client.set_cookies(cookie)
            client.default_game = genshin.Game.GENSHIN
            client.region = genshin.utility.recognize_region(user.uid, genshin.Game.GENSHIN)
            await abyss_update_user(client, user.uid, user.discord_guild, sess)
            await note_check_user(client, user)
    await close_session(sess)


async def artifact_update_user(e: EnkaArtifact, uid, gid):
    try:
        sess = await create_session()
        async for artifact in e.fetch_artifact_user(uid):
            if artifact.score > 30:
                await create_artifact(artifact, uid, gid, sess)
        await close_session(sess)
    except enkapy.exception.UIDNotFounded:
        return
    except Exception as e:
        print(e)


ArtifactUpdateCache = {}


@tasks.loop(hours=1)
async def artifact_update():
    global ArtifactUpdateCache
    log.info('Artifact Update started')
    sess = await create_session()
    e = await EnkaArtifact.create()
    users = {}
    for user in await fetch_all_users(sess):
        if user[0].enabled:
            users[user[0].uid] = user[0].discord_guild
    await close_session(sess)

    for uid, gid in users.items():
        now = datetime.datetime.now()
        if uid in ArtifactUpdateCache:
            gap = datetime.timedelta(minutes=10)
            if now - ArtifactUpdateCache[uid] < gap:
                continue
            else:
                ArtifactUpdateCache[uid] = now
        else:
            ArtifactUpdateCache[uid] = now
        log.info(f'Updating artifacts for {uid}')
        await artifact_update_user(e, uid, gid)


@artifact_update.error
async def artifact_error(e):
    print(e)


do_daily.start()
data_update.start()
artifact_update.start()
bot.run(DISCORD_BOT_TOKEN)
