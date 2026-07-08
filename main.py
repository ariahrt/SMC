import json
import os
import csv
from datetime import datetime, timezone
from dotenv import load_dotenv
from osu import AuthHandler, Client, Scope
from osrparse import Replay

load_dotenv()

def get_creds():
    return Client.from_credentials(
        os.getenv("CLIENT_ID"),
        os.getenv("CLIENT_SECRET"),
        None
    )

def get_osu_ident(code, redirect_uri):
    auth = AuthHandler(
        int(os.getenv("CLIENT_ID")),
        os.getenv("CLIENT_SECRET"),
        redirect_uri,
        Scope.identify()
    )
    auth.get_auth_token(code)
    user_client = Client(auth)
    user = user_client.get_own_data()
    return {"id": user.id, "username": user.username}

def add_map(client, beatmap_id, pool_path="pool.json"):
    beatmap = client.lookup_beatmap(id=beatmap_id)
    entry = {
        "artist": beatmap.beatmapset.artist,
        "title": beatmap.beatmapset.title,
        "difficulty": beatmap.version,
        "checksum": beatmap.checksum,
        "beatmapset_id": beatmap.beatmapset.id,
    }

    if os.path.exists(pool_path):
        with open(pool_path, "r") as f:
            pool = json.load(f)
    else:
        pool = []

    pool.append(entry)

    with open(pool_path, "w") as f:
        json.dump(pool, f, indent=2)

    return entry

def check_replay(replay_path, pool_path="pool.json"):
    replay = Replay.from_path(replay_path)

    with open(pool_path) as f:
        pool = json.load(f)

    for entry in pool:
        if entry["checksum"] == replay.beatmap_hash:
            return {"correct": True, "match": entry}

    return {"correct": False, "match": None}

def eval_submission(client, replay_path, pool_path="pool.json"):
    replay = Replay.from_path(replay_path)
    played = client.lookup_beatmap(checksum=replay.beatmap_hash)

    played_info = {
        "artist": played.beatmapset.artist,
        "title": played.beatmapset.title,
        "difficulty": played.version,
        "beatmapset_id": played.beatmapset.id,
        "beatmap_id": played.id,
    }

    with open(pool_path) as f:
        pool = json.load(f)

    for entry in pool:
        if entry["checksum"] == replay.beatmap_hash:
            return {"tier": "correct", "match": entry, "played": played_info, "played_at": replay.timestamp}
    for entry in pool:
        if entry["beatmapset_id"] == played.beatmapset.id:
            return {"tier": "close_diff", "match": entry, "played": played_info, "played_at": replay.timestamp}
    for entry in pool:
        if entry["artist"] == played.beatmapset.artist:
            return {"tier": "close_artist", "match": entry, "played": played_info, "played_at": replay.timestamp}

    return{"tier": "incorrect", "match": None, "played": played_info, "played_at": replay.timestamp}

def safe_filename(discord_id, timestamp, extension):
    safe_time = timestamp.strftime("%Y%m%d_%H%M%S")
    return f"{discord_id}_{safe_time}{extension}"

# submission logging for statistics and processing

def log_submission(discord_id, discord_username, message_timestamp, replay_path, screenshot_path, result, log_path="submissions.json"):
    entry = {
        "player_id": discord_id,
        "player": discord_username,
        "timestamp": message_timestamp.isoformat(),
        "played_at": result["played_at"].isoformat(),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "replay_file": replay_path,
        "screenshot_file": screenshot_path,
        "tier": result["tier"],
        "match": result["match"],
        "played": result["played"],
    }

    if os.path.exists(log_path):
        with open(log_path) as f:
            log = json.load(f)
    else:
        log = []

    log.append(entry)

    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    return entry

def import_teams(csv_path, teams_path="teams.json"):
    teams = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row["team_name"]
            member = {
                "discord_id": row["discord_id"],
                "osu_id": row["osu_id"],
                "osu_username": row["osu_username"],
            }
            teams.setdefault(team, []).append(member)

    with open(teams_path, "w") as f:
        json.dump(teams, f, indent=2)

    return teams

def find_team(discord_id, teams_path="teams.json"):
    if not os.path.exists(teams_path):
        return None

    with open(teams_path) as f:
        teams = json.load(f)

    for team_name, members in teams.items():
        for member in members:
            if str(member["discord_id"]) == str(discord_id):
                return team_name

    return None


if __name__ == "__main__":
    client = get_creds()
    print(add_map(client, beatmap_id="655686"))
    print(check_replay("test_replay.osr"))