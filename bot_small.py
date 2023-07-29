import os
from dotenv import load_dotenv
import time
import sqlite3
from atprototools import Session
from easydict import EasyDict
import gpt
from datetime import datetime, timedelta, timezone
import pytz
from dateutil.parser import parse
import random
import util
import json
import requests
import re
import cairosvg


# connection_atp = sqlite3.connect("atp.db")
# cur = connection_atp.cursor()

# cur.execute(
#     """
# CREATE TABLE IF NOT EXISTS users
#   (id INTEGER PRIMARY KEY AUTOINCREMENT,
#    did TEXT UNIQUE,
#    handle TEXT,
#    endpoint TEXT,
#    created_at DATETIME
#    )
# """
# )
# connection_atp.commit()

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

username = os.environ.get("BOT_HANDLE")
password = os.environ.get("BOT_PASSWORD")

# connection = sqlite3.connect("bluesky_bot.db")
# connection.row_factory = sqlite3.Row
# cur = connection.cursor()

# cur.execute(
#     """
# CREATE TABLE IF NOT EXISTS reactions
#   (id INTEGER PRIMARY KEY AUTOINCREMENT,
#    did TEXT,
#    handle TEXT,
#    displayName TEXT,
#    created_at DATETIME
#    )
# """
# )

# cur.execute(
#     """
# CREATE TABLE IF NOT EXISTS users
#   (id INTEGER PRIMARY KEY AUTOINCREMENT,
#    did TEXT UNIQUE,
#    mode INTEGER,
#    analyze INTEGER,
#    points INTEGER,
#    all_points INTEGER,
#    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
#    update_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
#    )
# """
# )

# cur.execute(
#     """
# CREATE TRIGGER IF NOT EXISTS update_users_timestamp
# AFTER UPDATE ON users
# FOR EACH ROW
# BEGIN
#   UPDATE users SET update_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
# END;
# """
# )

# cur.execute(
#     """
# CREATE TABLE IF NOT EXISTS count_post
#   (id INTEGER PRIMARY KEY AUTOINCREMENT,
#    count INTEGER,
#    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
#    )
# """
# )


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
    # pass


def reply_to(session, text, eline, image_path=None):
    root_cid = None
    root_uri = None
    if "reply" in eline:
        root_cid = eline.reply.root.cid
        root_uri = eline.reply.root.uri

    if root_cid:
        root = {"cid": root_cid, "uri": root_uri}
    else:
        root = {"cid": eline.post.cid, "uri": eline.post.uri}

    reply = {"cid": eline.post.cid, "uri": eline.post.uri}
    reply_ref = {"root": root, "parent": reply}
    chunk_size = 280
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        if i == 0 and image_path:
            response = post_image(session, chunk, image_path, reply_to=reply_ref)
        else:
            response = session.postBloot(chunk, reply_to=reply_ref)
        reply = json.loads(response.text)
        reply_ref["parent"] = reply


def post_image(
    session, postcontent, image_path, reply_to=None, content_type="image/png"
):
    """Post a bloot."""
    timestamp = datetime.utcnow()
    timestamp = timestamp.isoformat().replace("+00:00", "Z")

    headers = {"Authorization": "Bearer " + session.ATP_AUTH_TOKEN}

    data = {
        "collection": "app.bsky.feed.post",
        "$type": "app.bsky.feed.post",
        "repo": "{}".format(session.DID),
        "record": {
            "$type": "app.bsky.feed.post",
            "createdAt": timestamp,
            "text": postcontent,
        },
    }

    if image_path:
        data["record"]["embed"] = {}
        image_resp = session.uploadBlob(image_path, content_type)
        data["record"]["embed"]["$type"] = "app.bsky.embed.images"
        data["record"]["embed"]["images"] = [
            {"alt": "", "image": image_resp.json().get("blob")}
        ]
    if reply_to:
        data["record"]["reply"] = reply_to
    resp = requests.post(
        session.ATP_HOST + "/xrpc/com.atproto.repo.createRecord",
        json=data,
        headers=headers,
    )

    return resp


def get_profile(session, handle):
    response = session.get_profile(handle)
    return json.loads(response.text)


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

    # print("sleep")
    # time.sleep(3)

    post(session, f"🤖test")
    break
