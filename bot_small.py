import os
from dotenv import load_dotenv
import time
from atprototools import Session
from easydict import EasyDict
from datetime import datetime, timedelta
import pytz
from dateutil.parser import parse
import json
import requests

load_dotenv()

username = os.environ.get("BOT_HANDLE")
password = os.environ.get("BOT_PASSWORD")


def login(username, password):
    session = Session(username, password)
    print(f"login at:{datetime.now(pytz.utc)}", session)
    return session


def get_did(session, username):
    response = session.resolveHandle(username)
    return json.loads(response.text)["did"]


def post(session, text):
    print(text)
    session.postBloot(text)


def _get_follows(session, handle, limit=100, cursor=None):
    headers = {"Authorization": "Bearer " + session.ATP_AUTH_TOKEN}

    url = (
        session.ATP_HOST
        + f"/xrpc/app.bsky.graph.getFollows?actor={handle}&limit={limit}"
    )
    if cursor:
        url += f"&cursor={cursor}"

    response = requests.get(url, headers=headers)

    return json.loads(response.text)


def _get_followers(session, handle, limit=100, cursor=None):
    headers = {"Authorization": "Bearer " + session.ATP_AUTH_TOKEN}

    url = (
        session.ATP_HOST
        + f"/xrpc/app.bsky.graph.getFollowers?actor={handle}&limit={limit}"
    )
    if cursor:
        url += f"&cursor={cursor}"

    response = requests.get(url, headers=headers)

    return json.loads(response.text)


def get_follows(session, handle):
    cursor = None
    all_follow_list = []
    while True:
        response = _get_follows(session, handle, limit=100, cursor=cursor)
        follows = response["follows"]
        follow_list = [follow["handle"] for follow in follows]
        all_follow_list.extend(follow_list)
        prev_cursor = cursor
        if "cursor" in response:
            cursor = response["cursor"]
        if cursor is None or prev_cursor == cursor or len(follow_list) < 100:
            break

    return all_follow_list


def get_followers(session, handle):
    cursor = None
    all_follower_list = []
    while True:
        response = _get_followers(session, handle, limit=100, cursor=cursor)
        followers = response["followers"]
        follower_list = [follower["handle"] for follower in followers]
        all_follower_list.extend(follower_list)
        prev_cursor = cursor
        if "cursor" in response:
            cursor = response["cursor"]
        if cursor is None or prev_cursor == cursor or len(follower_list) < 100:
            break

    return all_follower_list


def is_follower(session, bot_handle, handle, followers):
    folowed = False
    if handle in followers:
        folowed = True
    return folowed


def update_follow(session, bot_handle):
    bot_follows = get_follows(session, bot_handle)
    bot_followers = get_followers(session, bot_handle)
    # unfollows = [item for item in bot_follows if item not in bot_followers]
    followbacks = [item for item in bot_followers if item not in bot_follows]
    for handle in followbacks:
        response = session.follow(handle)
        print(f"follow back:{handle}:{response}")
        time.sleep(0.05)


personality = """
"""

bot_names = [
    "Blueskyちゃん",
    f"{username}",
]


prompt = f"これはあなたの人格です。'{personality}'\nこの人格を演じて次の文章に対して30〜200文字以内で返信してください。"


session = login(username, password)
bot_did = get_did(session, username)

login_time = now = datetime.now(pytz.utc)
started = now
answered = None
count = 0


def detect_other_mention(eline):
    if "facets" in eline.post.record:
        for facet in eline.post.record.facets:
            if "features" in facet:
                for feature in facet.features:
                    if "did" in feature:
                        if bot_did != feature["did"]:
                            return True
    return False


# post(session, f"🤖test")


def oneshot():
    skyline = session.getSkyline(50)
    feed = skyline.json().get("feed")
    sorted_feed = sorted(feed, key=lambda x: parse(x["post"]["indexedAt"]))
    update_follow(session, username)

    for line in sorted_feed:
        eline = EasyDict(line)
        if eline.post.author.handle == username:
            # 自分自身には反応しない
            continue

        did = eline.post.author.did.replace("did:plc:", "")
        text = eline.post.record.text
        name = (
            eline.post.author.displayName
            if "displayName" in eline.post.author
            else eline.post.author.handle.split(".", 1)[0]
        )
        print(name, text)


oneshot()


def mainloop():
    while True:
        if (datetime.now(pytz.utc) - login_time) > timedelta(minutes=30):
            session = login(username, password)
            login_time = datetime.now(pytz.utc)

        skyline = session.getSkyline(50)
        feed = skyline.json().get("feed")
        sorted_feed = sorted(feed, key=lambda x: parse(x["post"]["indexedAt"]))
        bot_followers = get_followers(session, username)

        for line in sorted_feed:
            eline = EasyDict(line)
            if eline.post.author.handle == username:
                # 自分自身には反応しない
                continue
            # print(eline.post.indexedAt)
            postDatetime = parse(eline.post.indexedAt)
            print(now, postDatetime)
            if now < postDatetime:
                # フォロワのみ反応する
                print(postDatetime)
                if not is_follower(
                    session, username, eline.post.author.handle, followers=bot_followers
                ):
                    print("not follower")
                    continue

                if "reason" in eline:
                    print("reason")
                    continue

                if detect_other_mention(eline):
                    # 他の人にメンションがある時はスルー
                    print("other mention")
                    now = postDatetime
                    continue
                print(line)

                did = eline.post.author.did.replace("did:plc:", "")
                text = eline.post.record.text
                name = (
                    eline.post.author.displayName
                    if "displayName" in eline.post.author
                    else eline.post.author.handle.split(".", 1)[0]
                )
                print(name, text)
                now = postDatetime

        time.sleep(3)
