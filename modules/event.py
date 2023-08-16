import genshin
from db import *


def find_event_key(event_data):
    score_key = ''
    list_key = ''
    for k, v in event_data.items():
        if isinstance(v, list):
            for i in v:
                if isinstance(i, dict):
                    for i_k, i_v in i.items():
                        if 'score' in i_k:
                            if isinstance(i_v, int) or isinstance(i_v, float):
                                score_key = i_k
                                list_key = k
                                return list_key, score_key
    return list_key, score_key


async def event_update(client: genshin.Client, uid, gid, sess=db_sess):
    a = await client._request_genshin_record("activities", uid)
    if 'activities' not in a:
        return
    a = a['activities']
    if not isinstance(a, list):
        return
    last_event = a[-1]
    if not isinstance(last_event, dict):
        return
    keys = list(last_event.keys())
    if len(keys) > 1:
        return
    event_id = keys[0]
    event_data = last_event[event_id]
    if not isinstance(event_data, dict):
        return
    event_info = await get_event(event_id, sess)
    if event_info:
        list_key = event_info.record_list_key
        score_key = event_info.score_key
    else:
        list_key, score_key = find_event_key(event_data)
        if list_key and score_key:
            await add_event(event_id, list_key, score_key, sess)
            await disable_all_event(sess)
            await enable_event(event_id, sess)

    if not list_key:
        return
    if not score_key:
        return

    score_list = []
    for level in event_data[list_key]:
        score_list.append(level[score_key])

    total_score = int(sum(score_list))
    score_list.reverse()
    valid_index = -1
    for i, x in enumerate(score_list):
        if x:
            valid_index = i
            break
    if valid_index != -1:
        score_list = score_list[valid_index:]
        score_list.reverse()
    detail = '+'.join(map(str, score_list))
    if total_score:
        await create_update_event(event_id, uid, gid, total_score, detail, sess)
