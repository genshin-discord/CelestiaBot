create table if not exists abyss
(
    uid           int                         not null,
    season        int                         null,
    time          int                         not null,
    team          longtext                    null,
    discord_guild text                        null,
    star          int  default 0              not null,
    battle_count  int  default 0              null,
    info          json default (_utf8mb4'[]') null,
    primary key (uid, time, star)
);

create table if not exists artifacts
(
    uid           int          null,
    artifact      text         null,
    score         float        null,
    discord_guild text         null,
    icon          text         null,
    name          text         null,
    hash          varchar(100) not null
        primary key,
    constraint artifacts_hash_uindex
        unique (hash)
);

create table if not exists event
(
    uid           int           not null,
    event_id      varchar(50)   not null,
    score         int default 0 null,
    detail        text          null,
    discord_guild text          null,
    primary key (uid, event_id)
);

create table if not exists event_config
(
    event_id        varchar(50)   not null
        primary key,
    enabled         int default 0 null,
    record_list_key text          not null,
    score_key       text          not null,
    sort            int default 0 null,
    constraint event_config_event_id_uindex
        unique (event_id)
);

create table if not exists users
(
    uid           int           not null
        primary key,
    cookie        longtext      null,
    nickname      text          null,
    level         int           null,
    discord_id    text          null,
    discord_guild text          null,
    last_daily    int           null,
    enabled       int default 1 null,
    last_refresh  int default 0 null,
    notify        int default 0 null,
    last_redeem   int default 0 not null,
    gold          int default 0 null,
    silver        int default 0 null,
    bronze        int default 0 null,
    constraint users_uid_uindex
        unique (uid)
);

