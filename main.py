from http.cookies import SimpleCookie
from tempfile import mktemp
import discord
import enkapy
import genshin
import genshin.errors
import asyncio
import datetime
from discord.ext import bridge, tasks, commands
from discord.commands import Option
from discord.utils import escape_markdown
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import MaxNLocator
import numpy as np
from constant import *
import globals
from db import *
from modules.artifact import EnkaArtifact
from modules.codes import Codes
from modules.log import log
from modules.daily import do_daily
from modules.note import note_check_user
from modules.abyss import abyss_update_user, fun_abyss_filter
from modules.useragent import random_ua
from modules.event import event_update
from modules.genshin_data import GenshinData

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
# bot = bridge.Bot(intents=intents, command_prefix='/', debug_guilds=TEST_GUILDS)

bot = bridge.Bot(intents=intents, command_prefix='!')


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label='Need help?', style=discord.ButtonStyle.gray,
                                        url='https://github.com/genshin-discord/CelestiaBot/wiki/CelestiaBot-registration-help'))


async def help_embed(content):
    embed = discord.Embed(
        title="Registration error",
        description=f"Some error occurred during registration process",
        color=discord.Color.red())
    embed.add_field(name=chr(173), value=content, inline=False)
    embed.set_footer(text='Note: your cookie must have cookie_token')
    return embed


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
        await interaction.response.defer()
        cookie_str = self.children[0].value
        cookie_str = str(cookie_str).strip().strip('\'').strip('"')
        for _ in [';', 'ltoken', 'cookie_token']:
            if _ not in cookie_str:
                log.warning(f'User {interaction.user.id} {interaction.user.name} sent {cookie_str}')
                return await interaction.followup.send(
                    embed=await help_embed(f'Wrong cookies string![{_} NOT Found]'),
                    view=HelpView(),
                    ephemeral=True
                )
        if 'ltuid' not in cookie_str and 'ltmid_v2' not in cookie_str:
            return await interaction.followup.send(
                embed=await help_embed('Wrong cookies string![ltuid/ltmid_v2 NOT Found]'),
                view=HelpView(),
                ephemeral=True
            )
        if 'account_mid_v2' not in cookie_str and 'account_id' not in cookie_str:
            return await interaction.followup.send(
                embed=await help_embed('Wrong cookies string![account_id/account_mid_v2 NOT Found]'),
                view=HelpView(),
                ephemeral=True
            )

        cookie = SimpleCookie()
        cookie.load(cookie_str)
        cookies = {k: v.value for k, v in cookie.items()}

        # for _ in ['ltuid', 'ltoken', 'cookie_token', 'account_id']:
        #     if _ not in cookies:
        #         log.warning(f'User {interaction.user.id} {interaction.user.name} sent {cookie_str}')
        #         return await interaction.response.send_message(f'Wrong cookies![{_}]{COOKIE_HELP}')

        client = genshin.Client()
        client.set_cookies(cookies)
        client.default_game = genshin.Game.GENSHIN

        try:
            client.region = genshin.Region.OVERSEAS
            accounts = await client.get_game_accounts()
        except Exception as e:
            try:
                client.region = genshin.Region.CHINESE
                if not client.hoyolab_id:
                    hoyo = await client.get_hoyolab_user()
                    client.hoyolab_id = hoyo.hoyolab_id
                accounts = await client.get_game_accounts()
            except genshin.errors.InvalidCookies:
                return await interaction.followup.send(
                    embed=await help_embed('Wrong cookies![Login failure]'),
                    view=HelpView(),
                    ephemeral=True
                )

        messages = ''
        sess = await create_session()
        for acc in accounts:
            if acc.game == genshin.Game.GENSHIN:
                uid = acc.uid
                level = acc.level
                nick = acc.nickname
                if level > 35:
                    messages += f'Account {nick}[{uid}] added.\n'
                    await create_update_user(uid, json.dumps(cookies), nick, level, interaction.user.id,
                                             interaction.guild_id, sess=sess)
                    abyss = await get_user_best_abyss(uid, sess=sess)
                    # await update_user_artifact(uid, interaction.guild.id, sess=sess)
                    if not abyss:
                        await abyss_update_user(client, uid, interaction.guild.id, sess=sess)
                else:
                    messages += f'Account {nick}[{uid}] ignored(level < 35).\n'
        await close_session(sess)
        if not messages:
            messages = 'No genshin account detected.'
        await interaction.followup.send(messages)


async def event_embed(guild_id=None):
    sess = await create_session()
    event = await get_current_event(sess)
    if not event:
        embed = discord.Embed(
            title=f"Event Rank",
            description="",
            color=discord.Color.random())
        embed.add_field(name=chr(173), value='**No event rank for now.**')
    else:
        embed = discord.Embed(
            title=f"Event Rank",
            description=f"Current event {event.event_id}",
            color=discord.Color.random())

        if guild_id:
            limit = 5
        else:
            limit = 10
        cur = 1
        for event_data in await get_event_rank(guild_id, event.event_id, limit, sess=sess):
            info: Event = event_data[0]
            user = await fetch_user(info.uid, sess=sess)
            if user:
                uid = str(user.uid)
                if not guild_id:
                    uid = uid[:2] + '\\*' * (len(uid) - 3) + uid[-1:]
                mark = cur
                if mark in rank_emoji:
                    mark = rank_emoji[mark]
                embed.add_field(name=chr(173),
                                value=f"**{mark}.{escape_markdown(user.nickname)} {uid} {info.score}**\n"
                                      f"{info.detail}", inline=False)
                cur += 1

        embed.set_footer(text=f"Only top {limit} are shown.")
    await close_session(sess)
    return embed


async def global_abyss_embed(star_limit=999):
    if star_limit == 999:
        str_limit = 'Unlimited*'
    else:
        str_limit = f'Limited-{star_limit}*'
    embed = discord.Embed(
        title=f"Global abyss rank [{str_limit}]",
        description="Only counts seconds between 12-3-2 and 12-1-1",
        color=discord.Color.random())
    cur = 1
    sess = await create_session()
    for abyss in await get_abyss_rank(None, 10, star_limit, sess=sess):
        abyss = abyss[0]
        user = await fetch_user(abyss.uid, sess=sess)
        if user:
            uid = str(user.uid)
            uid = uid[:2] + '\\*' * (len(uid) - 3) + uid[-1:]
            mark = cur
            if mark in rank_emoji:
                mark = rank_emoji[mark]
            embed.add_field(name=chr(173),
                            value=f"**{mark}.{escape_markdown(user.nickname)} {uid} {abyss.time}s [{abyss.star}*]**\n"
                                  f"{abyss.team}", inline=False)
            cur += 1

    embed.set_footer(text="Only top 10 are shown.")
    await close_session(sess)
    return embed


async def fun_abyss_embed(guild=None):
    embed = discord.Embed(
        title=f"Global abyss rank [Fun mode]",
        description="Current Rules: Sumeru characters only.",
        color=discord.Color.random())
    cur = 1
    sess = await create_session()
    if not globals.global_genshin_data:
        globals.global_genshin_data = await GenshinData.create()
    for abyss in await fun_abyss_filter(guild, sess=sess):
        user = await fetch_user(abyss.uid, sess=sess)
        if user:
            uid = str(user.uid)
            uid = uid[:2] + '\\*' * (len(uid) - 3) + uid[-1:]
            mark = cur
            if mark in rank_emoji:
                mark = rank_emoji[mark]
            embed.add_field(name=chr(173),
                            value=f"**{mark}.{escape_markdown(user.nickname)} {uid} {abyss.time}s [{abyss.star}*]**\n"
                                  f"{abyss.team}", inline=False)
            cur += 1

    embed.set_footer(text="Only top 10 are shown.")
    await close_session(sess)
    return embed


async def abyss_embed(guild_id, star_limit=999):
    if star_limit == 999:
        str_limit = 'Unlimited*'
    else:
        str_limit = f'Limited-{star_limit}*'

    embed = discord.Embed(
        title=f"Abyss rank [{str_limit}]",
        description="Only counts seconds between 12-3-2 and 12-1-1",
        color=discord.Color.random())
    cur = 1
    sess = await create_session()
    for abyss in await get_abyss_rank(guild_id, star_limit=star_limit, sess=sess):
        abyss = abyss[0]
        user = await fetch_user(abyss.uid, sess=sess)
        if user:
            mark = cur
            if mark in rank_emoji:
                mark = rank_emoji[mark]
            embed.add_field(name=chr(173),
                            value=f"**{mark}.{escape_markdown(user.nickname)} {user.uid} {abyss.time}s [{abyss.star}*]**\n"
                                  f"{abyss.team}",
                            inline=False)
            cur += 1

    embed.set_footer(text="Only top 5 in this server are shown.")
    await close_session(sess)
    return embed


def user_medal_str(user: User):
    final = ''
    if user.gold:
        final += f'{user.gold}{rank_emoji[1]}'
    if user.silver:
        final += f'{user.silver}{rank_emoji[2]}'
    if user.bronze:
        final += f'{user.bronze}{rank_emoji[3]}'
    return final


async def abyss_hof_embed():
    embed = discord.Embed(
        title="Abyss hall of fame",
        description="Top players from historical abyss season",
        color=discord.Color.random())
    cur = 1
    sess = await create_session()
    for user in await get_abyss_hof(sess):
        if user:
            uid = str(user.uid)
            uid = uid[:2] + '\\*' * (len(uid) - 3) + uid[-1:]
            embed.add_field(name=chr(173),
                            value=f"**{cur}.{escape_markdown(user.nickname)} {uid} {user_medal_str(user)}**\n",
                            inline=False)
            cur += 1
    await close_session(sess)
    embed.set_footer(text="Only top 10 medal owners are shown.")
    return embed


class AbyssButton(discord.ui.View):
    def __init__(self, guild=None):
        self.guild = guild
        super().__init__(timeout=None)  # timeout of the view must be set to None

    @discord.ui.button(label="Unlimited", custom_id='unlimited_button', style=discord.ButtonStyle.primary,
                       disabled=True, emoji='😱')
    async def unlimited_callback(self, button, interaction):
        for child in self.children:
            child.disabled = False
        button.disabled = True
        if self.guild:
            embed = await abyss_embed(self.guild)
        else:
            embed = await global_abyss_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Limited-8", custom_id='limited_button8', style=discord.ButtonStyle.success, emoji='😎')
    async def limited8_callback(self, button, interaction):
        for child in self.children:
            child.disabled = False
        button.disabled = True
        if self.guild:
            embed = await abyss_embed(self.guild, 8)
        else:
            embed = await global_abyss_embed(8)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Limited-16", custom_id='limited_button16', style=discord.ButtonStyle.success, emoji='😎')
    async def limited16_callback(self, button, interaction):
        for child in self.children:
            child.disabled = False
        button.disabled = True
        if self.guild:
            embed = await abyss_embed(self.guild, 16)
        else:
            embed = await global_abyss_embed(16)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Fun", custom_id='fun_button', style=discord.ButtonStyle.secondary, emoji='🤣')
    async def fun_callback(self, button, interaction):
        for child in self.children:
            child.disabled = False
        button.disabled = True
        if self.guild:
            embed = await fun_abyss_embed(self.guild)
        else:
            embed = await fun_abyss_embed()
        await interaction.response.edit_message(embed=embed, view=self)


class EventButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # timeout of the view must be set to None

    @discord.ui.button(label="Server rank", custom_id='event_server', style=discord.ButtonStyle.primary,
                       disabled=True)
    async def server_callback(self, button, interaction: discord.Interaction):
        for child in self.children:
            child.disabled = False
        button.disabled = True
        embed = await event_embed(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Global rank", custom_id='event_global', style=discord.ButtonStyle.success)
    async def global_callback(self, button, interaction):
        for child in self.children:
            child.disabled = False
        button.disabled = True
        embed = await event_embed(None)
        await interaction.response.edit_message(embed=embed, view=self)


@bot.bridge_command(name="event_rank", description="Show top event records")
async def event_rank(ctx: discord.ApplicationContext):
    await ctx.respond(embed=await event_embed(ctx.guild_id), view=EventButton())


@bot.bridge_command(name="abyss_hof", description="Show abyss hall of fame")
async def abyss_hall_of_fame(ctx: discord.ApplicationContext):
    await ctx.respond(embed=await abyss_hof_embed())


@bot.bridge_command(name="global_abyss_rank", description="Show top 10 abyss record in all servers")
async def global_abyss_rank(ctx: discord.ApplicationContext):
    await ctx.respond(embed=await global_abyss_embed(), view=AbyssButton())


@bot.bridge_command(name="abyss_rank", description="Show top 5 abyss record in current server")
async def abyss_rank(ctx: discord.ApplicationContext):
    await ctx.respond(embed=await abyss_embed(ctx.guild_id), view=AbyssButton(ctx.guild_id))


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
                    "\n\nTop 5 good artifact(score>40) owner",
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


@bot.bridge_command(name='notify',
                    description="Notifications setting for resin maxed/transformer available/teapot coins maxed")
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
                    resp += f'Redeem failed {escape_markdown(user.nickname)}[{user.uid}], CN server not supported\n'
                    continue
                client.default_game = genshin.Game.GENSHIN
                try:
                    await client.redeem_code(code, uid=user.uid)
                    resp += f'Redeem success {escape_markdown(user.nickname)}[{user.uid}]\n'
                    await asyncio.sleep(3)
                except genshin.errors.RedemptionClaimed:
                    resp += f'Redeem already claimed {escape_markdown(user.nickname)}[{user.uid}]\n'
                except genshin.errors.RedemptionInvalid:
                    resp = 'Code invalid'
                    break
                except genshin.errors.RedemptionCooldown:
                    await asyncio.sleep(3)
                    continue
                except genshin.errors.GenshinException as e:
                    resp += f'Redeem failed {escape_markdown(user.nickname)}[{user.uid}], cookies or code invalid\n'
                    print(e)
        if not resp:
            resp = 'Your accounts are disabled.'
    await close_session(sess)
    return await ctx.followup.send(resp)


@bot.bridge_command(name='redeem_all', description="Redeem all codes available for your accounts")
async def redeem_all(ctx: discord.ApplicationContext):
    await ctx.defer()
    sess = await create_session()
    c = await Codes.create()
    redeem_codes = await c.get()
    if not redeem_codes:
        return await ctx.followup.send('No redeemable codes for now.')
    users = await get_discord_users(ctx.user.id, ctx.guild.id, sess=sess)
    resp = 'Account not found, add account via /reg first!'
    if users:
        resp = ''
        for user in users:
            if user.enabled and user.cookie:
                if not user.last_redeem:
                    user.last_redeem = 0
                if time.time() - user.last_redeem > 12 * 3600:
                    user.last_redeem = time.time()
                    sess.add(user)
                    await sess.commit()
                    for code in redeem_codes:
                        cookie = json.loads(user.cookie)
                        log.info(f'Trying to redeem code {code} for {user.uid}')
                        client = genshin.Client()
                        client.region = genshin.utility.recognize_region(user.uid, genshin.Game.GENSHIN)
                        if client.region == genshin.Region.CHINESE:
                            resp += f'Redeem failed {escape_markdown(user.nickname)}[{user.uid}], CN server not supported\n'
                            continue
                        client.set_cookies(cookie)
                        client.default_game = genshin.Game.GENSHIN
                        try:
                            await client.redeem_code(code, uid=user.uid)
                            resp += f'{code} redeem success {escape_markdown(user.nickname)}[{user.uid}]\n'
                            await asyncio.sleep(3)
                        except genshin.errors.RedemptionClaimed:
                            resp += f'{code} redeem already claimed {escape_markdown(user.nickname)}[{user.uid}]\n'
                        except genshin.errors.RedemptionInvalid:
                            resp += f'{code} code invalid\n'
                            break
                        except genshin.errors.RedemptionCooldown:
                            await asyncio.sleep(3)
                            continue
                        except genshin.errors.GenshinException as e:
                            resp += f'{code} redeem failed {escape_markdown(user.nickname)}[{user.uid}], cookies or code invalid\n'
                            print(e)
                else:
                    next_redeem = datetime.timedelta(seconds=user.last_redeem + 12 * 3600 - int(time.time()))
                    resp += f'{escape_markdown(user.nickname)}[{user.uid}] cannot use redeem_all now, next available in {next_redeem}\n'
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
                abyss = await get_user_best_abyss(user.uid, sess)
                artifact_count = await get_user_artifact_count(user.discord_guild, user.uid, sess)
                medals = user_medal_str(user)
                if not medals:
                    medals = 'No medals for now.'
                if not abyss:
                    embed.add_field(name=chr(173),
                                    value=f"**{escape_markdown(user.nickname)} {user.uid}**\n"
                                          f"Good artifacts: **{artifact_count}**\n"
                                          f"===============================\n"
                                          f"Abyss medals: {medals}\n"
                                          "No abyss info, try max floor 12 in a **single consecutive run** first.",
                                    inline=False)
                    continue
                abyss_rank_server = await get_user_abyss_rank(user.discord_guild, user.uid, sess)
                abyss_rank_global = await get_user_abyss_rank(None, user.uid, sess)
                server_mark = abyss_rank_server + 1
                global_mark = abyss_rank_global + 1
                if server_mark in rank_emoji:
                    server_mark = rank_emoji[server_mark]
                if global_mark in rank_emoji:
                    global_mark = rank_emoji[global_mark]

                embed.add_field(name=chr(173),
                                value=f"**{escape_markdown(user.nickname)} {user.uid}**\n"
                                      f"Good artifacts: **{artifact_count}**\n"
                                      f"===============================\n"
                                      f"Abyss medals: {medals}\n"
                                      f"Abyss time: **{abyss.time}s**\n"
                                      f"Abyss rank(server): **{server_mark}**\n"
                                      f"Abyss rank(global): **{global_mark}**\n"
                                      f"Abyss battle count: **{abyss.battle_count}**\n"
                                      f"Abyss team 5* count: **{abyss.star}**\n"
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
                    if not client.hoyolab_id:
                        hoyo = await client.get_hoyolab_user()
                        client.hoyolab_id = hoyo.hoyolab_id
                    await abyss_update_user(client, user.uid, user.discord_guild, sess=sess)
                    await artifact_update_user(e, user.uid, user.discord_guild, sess)
                    await update_refresh_time(user.uid, sess=sess)
                    await event_update(client, user.uid, user.discord_guild, sess)
                    resp += f'Account {escape_markdown(user.nickname)}[{user.uid}] refreshed.\n'
                else:
                    next_refresh = datetime.timedelta(seconds=user.last_refresh + 12 * 3600 - int(time.time()))
                    resp = 'You can only use /refresh once per 12 hours!\n' \
                           f'Next /refresh available in {next_refresh}'
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


async def artifact_update_user(e: EnkaArtifact, uid, gid, sess):
    try:
        # sess = await create_session()
        async for artifact in e.fetch_artifact_user(uid):
            if artifact.score > 40:
                await create_artifact(artifact, uid, gid, sess)
        # await close_session(sess)
    except enkapy.exception.UIDNotFounded:
        return
    except Exception as e:
        print(e)


@tasks.loop(hours=2)
async def work_thread():
    """Update abyss and check user note, do daily, artifact update"""
    e = await EnkaArtifact.create()
    sess = await create_session()
    for user in await fetch_all_users(sess):
        user = user[0]
        if user.cookie and user.enabled:
            cookie = json.loads(user.cookie)
            client = genshin.Client()
            client.set_cookies(cookie)
            client.default_game = genshin.Game.GENSHIN
            client.region = genshin.utility.recognize_region(user.uid, genshin.Game.GENSHIN)
            client.lang = 'en-us'
            client.USER_AGENT = await random_ua()
            try:
                if not client.hoyolab_id:
                    hoyo = await client.get_hoyolab_user()
                    client.hoyolab_id = hoyo.hoyolab_id
            except genshin.errors.GenshinException as e:
                await disable_user_cookies(cookie, sess)
                discord_user = await bot.fetch_user(int(user.discord_id))
                await discord_user.send(f'Account {user.nickname}[{user.uid}] session expired.')
                log.warning(f'Error work thread in {user.uid}')
                continue
            try:
                await do_daily(bot, user, sess)
                await abyss_update_user(client, user.uid, user.discord_guild, sess)
                await note_check_user(bot, client, user)
                log.info(f'Updating events for {user.uid}')
                await event_update(client, user.uid, user.discord_guild, sess)
                log.info(f'Updating artifacts for {user.uid}')
                await artifact_update_user(e, user.uid, user.discord_guild, sess)
            except genshin.errors.InvalidCookies:
                try:
                    await disable_user_cookies(user.cookie, sess)
                    discord_user = await bot.fetch_user(int(user.discord_id))
                    await discord_user.send(
                        embed=await help_embed(f'Account {user.nickname}[{user.uid}] session expired'),
                        view=HelpView()
                    )
                except discord.Forbidden:
                    break
            except genshin.errors.GenshinException:
                log.warning(f'Error work thread in {user.uid}')
    await close_session(sess)


@bot.event
async def on_ready():
    bot.add_view(AbyssButton())
    bot.add_view(EventButton())
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="holy relics brushing"))
    if not globals.global_genshin_data:
        globals.global_genshin_data = await GenshinData.create()
    log.info(f"{bot.user} Logged in")


work_thread.start()
bot.run(DISCORD_BOT_TOKEN)
