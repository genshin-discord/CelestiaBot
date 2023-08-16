import random

from db import *
import genshin
import discord
from constant import *
from modules.log import log
from modules.useragent import random_ua
from modules.geetest import Geetest
import asyncio
import datetime


async def check_daily_time(user: User):
    if user:
        if user.last_daily:
            last = datetime.datetime.fromtimestamp(user.last_daily)
            now = datetime.datetime.now()
            refresh = now.replace(hour=0, minute=0, second=0, microsecond=0)
            last_gap = refresh - last
            last_gap = last_gap.total_seconds()
            if time.time() - user.last_daily > 24 * 3600 or last_gap > 0:
                return True
            else:
                return False
        else:
            return True
    return False


async def do_daily_user(user: User):
    if user:
        cookie = json.loads(user.cookie)
        client = genshin.Client()
        client.set_cookies(cookie)
        client.default_game = genshin.Game.GENSHIN
        client.region = genshin.utility.recognize_region(user.uid, genshin.Game.GENSHIN)
        if client.region == genshin.Region.CHINESE:
            return
        client.uid = user.uid
        client.USER_AGENT = await random_ua()
        if not client.hoyolab_id:
            hoyo = await client.get_hoyolab_user()
            client.hoyolab_id = hoyo.hoyolab_id
        await client.claim_daily_reward(reward=False, game=genshin.Game.GENSHIN)
        fail = 0
        # while fail < 5:
        #     resp = await client.request_daily_reward("sign", method="POST", game=genshin.Game.GENSHIN)
        #     break
        # if isinstance(resp, dict) and 'gt' in resp and 'challenge' in resp:
        #     fail += 1
        #     g = await Geetest.create()
        #     r = await g.crack(resp['gt'], resp['challenge'])
        #     if r['data']['result'] != 'click':
        #         break
        #     print(r)
        #     await g.close()
        #     await asyncio.sleep(random.randint(1, 5))
        # else:
        #     break


async def do_daily(bot: discord.Bot, user: User, sess):
    if await check_daily_time(user):
        if user.enabled:
            retry, retry_times = 1, 0
            while retry and retry_times < 5:
                log.info(f'Doing daily for {user.uid}')
                retry = 0
                try:
                    await do_daily_user(user)
                except genshin.errors.AlreadyClaimed:
                    log.info(f'{user.uid} already claimed')
                    await update_daily_time(user.uid, sess)
                except genshin.errors.InvalidCookies:
                    try:
                        await disable_user_cookies(user.cookie, sess)
                        discord_user = await bot.fetch_user(int(user.discord_id))
                        await discord_user.send(
                            f'Account {user.nickname}[{user.uid}] session expired.{COOKIE_HELP}')
                    except discord.Forbidden:
                        break
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
