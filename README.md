# Snafu's Multigame Cup - osu! scavenger hunt helper
[![Discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/) [![osu!](https://img.shields.io/badge/osu!-EA88CE?style=for-the-badge&logo=osu&logoColor=white)](https://osu.ppy.sh/)
> [!NOTE]
> At the time of writing this the links do not work as the tournament has not been released.

> [!WARNING]
> This does not include the `CLIENT_ID`, `CLIENT_SECRET`, `DISCORD_TOKEN`, or `SESSION_SECRET`.

For obvious reasons, the `pool.json` will not be inside of the commit, as this is for a tournament. 

## Discord Bot & `eval_submission`
This is a python program that utilizes `fastapi`, `osrparse`, `osu`, and `discord`.  
The program is designed to take *.osr* files and a *screenshot* from channels. Once the program receives the files, `bot.py` will call `eval_submission` and `log_submission`.  
`eval_submission` reads the replay data with `osrparse`. It pulls the beatmap hash from the replay, then uses `osu` to lookup the map by hash. 
```python
def eval_submission(client, replay_path, pool_path="pool.json"):
  replay = Replay.from_path(replay_path)
  played = client.lookup_beatmap(checksum=replay.beatmap_hash)
```
Those two lines are vital to making this program work. As *.osr* files do not contain anything in regards to the beatmap information other than the checksum.  
Once the program knows what map was played, it will log all the information about the submission into a json file. 
```python
played_info = {
  "artist": played.beatmapset.artist,
  "title": played.beatmapset.title,
  "difficulty": played.verison,
  "beatmapset_id": played.beatmapset.id,
  "beatmap_id": played.id,
}
```
It will then load the `pool.json` and check to see if the `beatmap_id` in the replay matches the `beatmap_id` in the json. Since the program logs artist, title, and the map set's ID, it can give feedback if whether the player is `correct`, `close_diff`, `close_artist`, or `incorrect`. Once the program determines the appropriate feedback, the discord bot will take the case, and send a message.
```python
match tier := result["tier"]:
  case "correct":
    m = result["match"]
    await message.channel.send(f"Correct map!")
  case "close_diff":
    await message.channel.send(f"Close diff!")
  case "close_artist":
    await message.channel.send(f"Close artist!")
  case "incorrect":
    await message.channel.send(f"Incorrect map!")
```
## 
