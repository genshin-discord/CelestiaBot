import asyncio
import datetime
import hashlib
import json
import time

from sqlalchemy import Column, Integer, String, and_, Float, desc, func, text, update
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from config import *
from modules.artifact import ArtifactData
from aiocache import cached

Base = declarative_base()


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
    notify = Column(Integer)

    def __repr__(self):
        return f'<User(uid:{self.uid}, nickname:{self.nickname}, discord_id:{self.discord_id})>'


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
    time = Column(Integer)
    star = Column(Integer)
    battle_count = Column(Integer)

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
        return f'https://enka.shinshin.moe/ui/{self.icon}.png'


engine = create_async_engine(URL.create('mysql+asyncmy', MYSQL_USER, MYSQL_PASS, MYSQL_HOST, MYSQL_PORT, MYSQL_DB),
                             echo=False, pool_recycle=1800, pool_pre_ping=True)


async def create_session():
    global engine
    async_sess = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    sess = async_sess()
    return sess


async def close_session(sess):
    global engine
    await sess.close()


#    await engine.dispose()


db_sess = None  # asyncio.run(create_session())


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
    user.cookie = cookie
    user.nickname = nickname
    user.level = level
    user.discord_id = discord_id
    user.discord_guild = discord_guild
    user.enabled = 1
    sess.add(user)
    return await sess.commit()


async def create_update_abyss(uid, season, time_used, team, star, battle_count, discord_guild, sess=db_sess):
    abyss = await fetch_user_abyss(uid, sess=sess)
    if not abyss:
        abyss = Abyss()
        abyss.uid = uid
    else:
        if time_used >= abyss.time and season == abyss.season:
            if discord_guild == abyss.discord_guild:
                return
            else:
                time_used = abyss.time
        # if discord_guild != abyss.discord_guild and time_used >= abyss.time and season == abyss.season:
        #     time_used = abyss.time
    abyss.season = season
    abyss.star = star
    abyss.battle_count = battle_count
    abyss.time = time_used
    abyss.team = team
    abyss.discord_guild = discord_guild
    sess.add(abyss)
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


async def get_discord_users(discord_id, discord_guild_id, sess=db_sess):
    query = select(User).where(and_(User.discord_id == discord_id, User.discord_guild == discord_guild_id))
    data = await sess.execute(query)
    users = data.scalars().all()
    return users


async def check_daily_time(uid, sess=db_sess):
    user: User = await fetch_user(uid, sess)
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


async def get_current_abyss_season(sess=db_sess):
    query = select(Abyss).order_by(Abyss.season.desc()).limit(1)
    data = await sess.execute(query)
    abyss: Abyss = data.scalars().first()
    return abyss.season


async def get_abyss_rank(discord_guild, limit=5, star_limit=999, sess=db_sess):
    current_season = await get_current_abyss_season(sess)
    if discord_guild:
        query = select(Abyss).where(
            and_(Abyss.discord_guild == discord_guild, Abyss.season == current_season,
                 Abyss.star <= star_limit)).order_by(Abyss.time).limit(limit)
    else:
        query = select(Abyss).where(and_(Abyss.season == current_season, Abyss.star <= star_limit)).order_by(
            Abyss.time).limit(limit)
    data = await sess.execute(query)
    return data


async def get_user_abyss_rank(discord_guild, uid, sess=db_sess):
    current_season = await get_current_abyss_season(sess)
    user_abyss = await get_abyss(uid, sess)
    if not user_abyss:
        return -1
    if discord_guild:
        query = select(func.count(Abyss.uid)).where(
            and_(Abyss.time < user_abyss.time, Abyss.discord_guild == discord_guild, Abyss.season == current_season))
    else:
        query = select(func.count(Abyss.uid)).where(and_(Abyss.time < user_abyss.time, Abyss.season == current_season))
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


async def get_abyss(uid, sess=db_sess):
    current_season = await get_current_abyss_season(sess=sess)
    query = select(Abyss).where(and_(Abyss.uid == uid, Abyss.season == current_season))
    data = await sess.execute(query)
    return data.scalars().first()


@cached(ttl=600)
async def get_admin(discord_id) -> Admin:
    sess = await create_session()
    query = select(Admin).where(Admin.discord_id == discord_id)
    data = await sess.execute(query)
    data = data.scalars().first()
    await close_session(sess)
    return data
