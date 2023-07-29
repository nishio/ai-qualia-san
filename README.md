# ai-qualia-san

This is AI-assisted virtual character. Using OpenAI API.
Forked from [bluesky-chan](https://github.com/kojira/bluesky-chan).


## startup

following is from original README.md

```sh
git clone https://github.com/kojira/bluesky-chan.git
cd bluesky-chan
cp .env.example .env
```

Change the contents of .env according to the environment.

```
OPENAI_API_KEY=your openai api key
BOT_HANDLE=bot handle(ex:kojira.bsky.social)
BOT_PASSWORD=bot password
```

Run with this command

```sh
docker compose up -d
```


```
2023-07-29 22:39:07 Traceback (most recent call last):
2023-07-29 22:39:07   File "/var/bot/bot.py", line 632, in <module>
2023-07-29 22:39:07     count = util.aggregate_users(connection_atp)
2023-07-29 22:39:07   File "/var/bot/util.py", line 225, in aggregate_users
2023-07-29 22:39:07     last_created_at = get_last_created_at(connection)
2023-07-29 22:39:07   File "/var/bot/util.py", line 148, in get_last_created_at
2023-07-29 22:39:07     return row[4]
2023-07-29 22:39:07 TypeError: 'NoneType' object is not subscriptable
```