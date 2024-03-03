import hashlib
import json
import time

from sqlalchemy import Column, Integer, String, and_, Float, desc, func, text, update, delete, distinct, or_, JSON
from sqlalchemy.dialects.mysql.dml import insert
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from config import *
from modules.artifact import ArtifactData
from aiocache import cached

Base = declarative_base()


# SET GLOBAL sql_mode=(SELECT REPLACE(@@sql_mode,'ONLY_FULL_GROUP_BY',''));

class User(Base):
    __tablename__ = 'users'
    uid = Column(Integer, primary_key=True)
    cookie = Column(String)
    nickname = Column(String)
    level = Column(Integer)
    discord_id = Column(String)
    discord_guild = Column(String)
    last_daily = Column(Integer)
    enabled = Column(Integer)
    last_refresh = Column(Integer)
    last_redeem = Column(Integer)
    notify = Column(Integer)
    gold = Column(Integer)
    silver = Column(Integer)
    bronze = Column(Integer)

    def __repr__(self):
        return f'<User(uid:{self.uid}, nickname:{self.nickname}, discord_id:{self.discord_id})>'


class Event(Base):
    __tablename__ = 'event'
    uid = Column(Integer, primary_key=True)
    event_id = Column(String, primary_key=True)
    score = Column(Integer)
    detail = Column(String)
    discord_guild = Column(String)


class EventConfig(Base):
    __tablename__ = 'event_config'
    event_id = Column(String, primary_key=True)
    enabled = Column(Integer)
    record_list_key = Column(String)
    score_key = Column(String)
    sort = Column(Integer)


class AbyssConfig(Base):
    __tablename__ = 'abyss_config'
    season = Column(String, primary_key=True)
    fun_module = Column(String)


class Admin(Base):
    __tablename__ = 'admin'
    discord_id = Column(String, primary_key=True)
    level = Column(Integer)


def sha256(data):
    m = hashlib.sha256()
    if isinstance(data, str):
        data = data.encode()
    m.update(data)
    return m.hexdigest()


class Abyss(Base):
    __tablename__ = 'abyss'
    uid = Column(Integer, primary_key=True)
    season = Column(Integer)
    team = Column(String)
    discord_guild = Column(String)
    time = Column(Integer, primary_key=True)
    star = Column(Integer, primary_key=True)
    battle_count = Column(Integer)
    info = Column(JSON)

    def __repr__(self):
        return f'<Abyss(uid:{self.uid}, guild:{self.discord_guild})>'


class Artifact(Base):
    __tablename__ = 'artifacts'
    uid = Column(Integer)
    artifact = Column(String)
    score = Column(Float)
    discord_guild = Column(String)
    icon = Column(String)
    name = Column(String)
    hash = Column(String, primary_key=True)

    @property
    def icon_url(self):
        return f'https://enka.network/ui/{self.icon}.png'


engine = create_async_engine(URL.create('mysql+asyncmy', MYSQL_USER, MYSQL_PASS, MYSQL_HOST, MYSQL_PORT, MYSQL_DB),
                             echo=False, pool_recycle=1800, pool_pre_ping=True)


async def create_session():
    global engine
    async_sess = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with async_sess.begin() as session:
        set_mode = text('''SET GLOBAL sql_mode=(SELECT REPLACE(@@sql_mode,'ONLY_FULL_GROUP_BY',''));''')
        await session.execute(set_mode)
    return async_sess


db_sess = None


async def create_artifact(artifact: ArtifactData, uid, gid, sess):
    db_artifact = Artifact()
    db_artifact.uid = uid
    db_artifact.icon = artifact.icon
    db_artifact.score = artifact.score
    db_artifact.discord_guild = gid
    db_artifact.artifact = json.dumps({'main': artifact.main_stat, 'sub': artifact.sub_stats})
    db_artifact.name = artifact.name
    db_artifact.hash = sha256(f'{uid}{db_artifact.name}{db_artifact.artifact}')

    query = select(Artifact).where(Artifact.hash == db_artifact.hash)
    data = await sess.execute(query)
    if data.scalars().first():
        return
    sess.add(db_artifact)
    return await sess.commit()


async def artifact_count_rank(gid, sess):
    query = select(Artifact.uid, func.count(Artifact.uid)).where(Artifact.discord_guild == gid).order_by(
        desc(text('count_1'))).group_by(Artifact.uid).limit(5)
    data = await sess.execute(query)
    return data.all()


async def fetch_user(uid, sess=db_sess):
    query = select(User).where(User.uid == uid)
    data = await sess.execute(query)
    user: User = data.scalars().first()
    return user


async def remove_user(discord_id, discord_guild_id, sess=db_sess):
    users = await get_discord_users(discord_id, discord_guild_id, sess)
    if users:
        for user in users:
            query = delete(Abyss).where(Abyss.uid == user.uid)
            await sess.execute(query)
            query = delete(Artifact).where(Artifact.uid == user.uid)
            await sess.execute(query)
            await sess.delete(user)
        await sess.commit()


async def fetch_user_abyss(uid, season=None, sess=db_sess):
    if season:
        query = select(Abyss).where(and_(Abyss.uid == uid, Abyss.season == season))
    else:
        query = select(Abyss).where(Abyss.uid == uid)
    data = await sess.execute(query)
    abyss: Abyss = data.scalars().first()
    return abyss


async def create_update_user(uid, cookie, nickname, level, discord_id, discord_guild, sess=db_sess):
    user: User = await fetch_user(uid, sess)
    if not user:
        user = User()
        user.uid = uid
        user.last_daily = 0
        user.last_refresh = 0
        user.notify = 0
        user.last_redeem = 0
    user.cookie = cookie
    user.nickname = nickname
    user.level = level
    user.discord_id = discord_id
    user.discord_guild = discord_guild
    user.enabled = 1

    sess.add(user)
    return await sess.commit()


async def check_user_abyss_exists(uid, season, time_used, team, sess=db_sess):
    query = select(Abyss).where(
        and_(Abyss.uid == uid, Abyss.season == season, Abyss.team == team, Abyss.time == time_used))
    data = await sess.execute(query)
    return data.scalars().first()


async def create_update_abyss(uid, season, time_used, team, star, battle_count, discord_guild, info, sess=db_sess):
    abyss = await fetch_user_abyss(uid, sess=sess)
    if abyss and abyss.discord_guild != discord_guild:
        update_guild = update(Abyss).where(Abyss.uid == uid).values(discord_guild=discord_guild)
        await sess.execute(update_guild)
        await sess.commit()
    if await check_user_abyss_exists(uid, season, time_used, team, sess=sess):
        return
    current_season = await get_current_abyss_season(sess)
    if season > current_season:
        await season_update(current_season, [8, 16], sess=sess)
    insert_stmt = insert(Abyss).values(
        uid=uid,
        season=season,
        time=time_used,
        team=team,
        info=info,
        star=star,
        discord_guild=discord_guild,
        battle_count=battle_count
    )
    final_stmt = insert_stmt.on_duplicate_key_update(
        season=insert_stmt.inserted.season,
        team=insert_stmt.inserted.team,
        info=insert_stmt.inserted.info,
        battle_count=insert_stmt.inserted.battle_count,
        discord_guild=insert_stmt.inserted.discord_guild,
    )
    await sess.execute(final_stmt)
    return await sess.commit()


async def update_user_artifact(uid, discord_guild, sess=db_sess):
    query = update(Artifact).where(Artifact.uid == uid).values(discord_guild=discord_guild)
    await sess.execute(query)
    await sess.commit()


async def fetch_all_users(sess=db_sess):
    query = select(User)
    data = await sess.execute(query)
    #    data.unique(lambda x: json.loads(x[0].cookie)['ltuid'])
    return data


async def update_daily_time(uid, sess=db_sess):
    query = update(User).where(User.uid == uid).values(last_daily=int(time.time()))
    await sess.execute(query)
    await sess.commit()


async def update_refresh_time(uid, sess=db_sess):
    query = update(User).where(User.uid == uid).values(last_refresh=int(time.time()))
    await sess.execute(query)
    await sess.commit()


async def disable_user_cookies(cookie, sess=db_sess):
    query = update(User).where(User.cookie == cookie).values(enabled=0)
    await sess.execute(query)
    await sess.commit()
    # query = select(User).where(User.cookie == cookie)
    # data = await sess.execute(query)
    # users = data.scalars().all()
    # if users:
    #     for user in users:
    #         user.enabled = 0
    #         sess.add(user)
    #     await sess.commit()


async def get_current_event(sess=db_sess):
    query = select(EventConfig).where(EventConfig.enabled == 1)
    data = await sess.execute(query)
    event: EventConfig = data.scalars().first()
    return event


async def get_event(event_id, sess=db_sess):
    query = select(EventConfig).where(EventConfig.event_id == event_id)
    data = await sess.execute(query)
    event: EventConfig = data.scalars().first()
    return event


async def add_event(event_id, list_key, score_key, sess=db_sess):
    e = EventConfig()
    e.event_id = event_id
    e.score_key = score_key
    e.record_list_key = list_key
    e.enabled = False
    sess.merge(e)
    return await sess.commit()


async def disable_all_event(sess=db_sess):
    query = update(EventConfig).values(enabled=0)
    await sess.execute(query)
    await sess.commit()


async def enable_event(event_id, sess=db_sess):
    query = update(EventConfig).where(EventConfig.event_id == event_id).values(enabled=1)
    await sess.execute(query)
    return await sess.commit()


async def create_update_event(event_id, uid, discord_guild, score, detail, sess=db_sess):
    query = select(Event).where(and_(Event.uid == uid, Event.event_id == event_id))
    data = await sess.execute(query)
    event: Event = data.scalars().first()
    if not event:
        event = Event()
        event.event_id = event_id
        event.uid = uid
        event.score = score
        event.detail = detail
        event.discord_guild = discord_guild
    else:
        if score > event.score:
            event.score = score
            event.detail = detail
            event.discord_guild = discord_guild
        else:
            return
    sess.add(event)
    return await sess.commit()


async def get_event_rank(discord_guild, event_id, limit=5, sess=db_sess):
    if discord_guild:
        query = select(Event).where(
            and_(Event.discord_guild == discord_guild, Event.event_id == event_id)).order_by(Event.score.desc()).limit(
            limit)
    else:
        query = select(Event).where(Event.event_id == event_id).order_by(Event.score.desc()).limit(limit)
    data = await sess.execute(query)
    return data


async def get_discord_users(discord_id, discord_guild_id, sess=db_sess):
    query = select(User).where(and_(User.discord_id == discord_id, User.discord_guild == discord_guild_id))
    data = await sess.execute(query)
    users = data.scalars().all()
    return users


async def get_current_abyss_season(sess=db_sess):
    query = select(Abyss).order_by(Abyss.season.desc()).limit(1)
    data = await sess.execute(query)
    abyss: Abyss = data.scalars().first()
    return abyss.season


async def get_abyss_fun_module(season, sess=db_sess) -> AbyssConfig:
    query = select(AbyssConfig).where(AbyssConfig.season == season)
    data = await sess.execute(query)
    abyss: AbyssConfig = data.scalars().first()
    return abyss


async def update_abyss_fun_module(season, module, sess=db_sess):
    abyss = AbyssConfig()
    abyss.season = season
    abyss.fun_module = module
    sess.add(abyss)
    return await sess.commit()


async def get_abyss_rank(discord_guild, limit=5, star_limit=999, sess=db_sess):
    current_season = await get_current_abyss_season(sess)
    if discord_guild:
        query = select(Abyss).where(
            and_(Abyss.discord_guild == discord_guild, Abyss.season == current_season,
                 Abyss.star <= star_limit)).group_by(Abyss.uid).order_by(Abyss.time).limit(limit)
    else:
        query = select(Abyss).where(and_(Abyss.season == current_season, Abyss.star <= star_limit)).order_by(
            Abyss.time).group_by(Abyss.uid).limit(limit)
    data = await sess.execute(query)
    return data


async def get_current_season_full_abyss(guild=None, sess=db_sess):
    current_season = await get_current_abyss_season(sess)
    if guild:
        query = select(Abyss).where(and_(Abyss.season == current_season, Abyss.discord_guild == guild)).order_by(
            Abyss.time)
    else:
        query = select(Abyss).where(Abyss.season == current_season).order_by(Abyss.time)
    data = await sess.execute(query)
    return data


async def get_user_abyss_rank(discord_guild, uid, sess=db_sess):
    current_season = await get_current_abyss_season(sess)
    user_abyss = await get_user_best_abyss(uid, sess)
    if not user_abyss:
        return -1
    if discord_guild:
        query = select(func.count(distinct(Abyss.uid))).where(
            and_(Abyss.time < user_abyss.time, Abyss.discord_guild == discord_guild,
                 Abyss.season == current_season))
    else:
        query = select(func.count(distinct(Abyss.uid))).where(
            and_(Abyss.time < user_abyss.time, Abyss.season == current_season))
    data = await sess.execute(query)
    return data.scalars().first()


async def get_user_artifact_count(discord_guild, uid, sess=db_sess):
    query = select(func.count(Artifact.hash)).where(and_(Artifact.discord_guild == discord_guild, Artifact.uid == uid))
    data = await sess.execute(query)
    return data.scalars().first()


async def get_artifact_rank(discord_guild, sess=db_sess):
    query = select(Artifact).where(Artifact.discord_guild == discord_guild).order_by(desc(Artifact.score)).limit(5)
    data = await sess.execute(query)
    return data


async def get_user_best_abyss(uid, sess=db_sess):
    current_season = await get_current_abyss_season(sess=sess)
    query = select(Abyss).where(and_(Abyss.uid == uid, Abyss.season == current_season)).order_by(Abyss.time).limit(1)
    data = await sess.execute(query)
    return data.scalars().first()


async def get_user_limited_abyss(uid, star=None, sess=db_sess):
    if not star:
        return await get_user_best_abyss(uid, sess)

    current_season = await get_current_abyss_season(sess=sess)
    query = select(Abyss).where(and_(Abyss.uid == uid, Abyss.season == current_season, Abyss.star <= star)).order_by(
        Abyss.time).limit(1)
    data = await sess.execute(query)
    return data.scalars().first()


async def get_abyss_hof(sess=db_sess):
    query = select(User).where(or_(User.gold > 0,
                                   User.silver > 0,
                                   User.bronze > 0)).order_by(desc(User.gold),
                                                              desc(User.silver),
                                                              desc(User.bronze)).limit(10)
    data = await sess.execute(query)
    return data.scalars()


async def update_user_medal(uid, place, sess=db_sess):
    if place == 0:
        query = update(User).values(gold=User.gold + 1).where(User.uid == uid)
    elif place == 1:
        query = update(User).values(silver=User.silver + 1).where(User.uid == uid)
    elif place == 2:
        query = update(User).values(bronze=User.bronze + 1).where(User.uid == uid)
    else:
        return
    await sess.execute(query)


async def season_medal_update(current_season, star_limit=999, sess=db_sess):
    query = select(Abyss).where(and_(Abyss.season == current_season, Abyss.star <= star_limit)).order_by(
        Abyss.time).group_by(
        Abyss.uid).limit(3)
    idx = 0
    for abyss in await sess.execute(query):
        abyss = abyss[0]
        await update_user_medal(abyss.uid, idx, sess)
        idx += 1
    await sess.commit()


async def season_update(season, limited=[8, 16], fun=True, sess=db_sess):
    for limit in limited:
        await season_medal_update(season, limit, sess)
    await season_medal_update(season, 999, sess)
    if fun:
        idx = 0
        from modules.abyss import fun_abyss_filter
        for abyss in await fun_abyss_filter(sess=sess):
            await update_user_medal(abyss.uid, idx, sess)
            idx += 1
    await sess.commit()


@cached(ttl=600)
async def get_admin(discord_id) -> Admin:
    _ = await create_session()
    async with _() as sess:
        query = select(Admin).where(Admin.discord_id == discord_id)
        data = await sess.execute(query)
        data = data.scalars().first()
    return data
