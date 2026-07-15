import cloudscraper
import json
from dotenv import load_dotenv
from urllib.parse import quote
from opgg.opgg import OPGG
from opgg.params import Region
import os
import requests

load_dotenv()
hypixel_api = os.getenv("HYPIXEL_API_KEY")
riot_api = os.getenv("RIOT_API_KEY")

# rocket league

rl_wanted = {"Ranked Duel 1v1", "Ranked Doubles 2v2", "Ranked Standard 3v3"}

def rl_get_peaks(data):
    segments = data["data"]["segments"]
    peaks = {}

    for seg in segments:
        if seg["type"] == "peak-rating" and seg["metadata"]["name"] in rl_wanted:
            peaks[seg["metadata"]["name"]] = seg["stats"]["peakRating"]["value"]
    
    return peaks

def rl_get_ratings(data):
    segments = data["data"]["segments"]
    ratings = {}

    for seg in segments:
        if seg["type"] == "playlist" and seg["metadata"]["name"] in rl_wanted:
            ratings[seg["metadata"]["name"]] = seg["stats"]["rating"]["value"]

    return ratings

def rl_peak_metadata(data, pp):
    segments = data["data"]["segments"]

    for seg in segments:
        if seg["type"] == "peak-rating" and seg["metadata"]["name"] == pp:
            metadata = seg["stats"]["peakRating"]["metadata"]
    
    return metadata

def rl_current_metadata(data, pp):
    segments = data["data"]["segments"]

    for seg in segments:
        if seg["type"] == "playlist" and seg["metadata"]["name"] == pp:
            metadata = seg["stats"]["tier"]["metadata"]

    return metadata

def rl_fetch_data(user, platform, team):
    try:
        safe_user = quote(user)
        url = f"https://api.tracker.gg/api/v2/rocket-league/standard/profile/{platform}/{safe_user}"
        scraper = cloudscraper.create_scraper()
        data = scraper.get(url).json()
        pi = data["data"]["platformInfo"]
        peaks = rl_get_peaks(data)
        ratings = rl_get_ratings(data)
        pp = max(peaks, key=peaks.get)
        pv = peaks[pp]
        pm = rl_peak_metadata(data, pp)
        cm = rl_current_metadata(data, pp)

        entry = {
            "team": team,
            "username": pi["platformUserHandle"],
            "uuid": pi["platformUserId"],
            "platform": pi["platformSlug"],
            "avatar": pi["avatarUrl"],
            "peakRating": {
                "peakPlaylist": pp,
                "value": pv,
                "metadata": {
                    "iconUrl": pm["iconUrl"],
                    "season": pm["season"],
                    "division": pm["divisionShort"],
                },
            },
            "currentRank": {
                "playlist": pp,
                "iconUrl": cm["iconUrl"],
                "rankName": cm["name"],
            },
            "ratings": ratings,
        }
        return entry
    except requests.exceptions.RequestException as e:
        return {"error": f"Could not reach Rocket League API: {e}"}
    except KeyError as e:
        return {"error": f"Unexpected response shape, missing field: {e}"}
    except Exception as e:
        return {"error": f"Rocket League lookup failed: {e}"}

def rl_save_data(user, platform, team, rlusers_path="rl_users.json"):
    entry = rl_fetch_data(user, platform, team)

    if "error" in entry:
        return entry

    if os.path.exists(rlusers_path):
        with open(rlusers_path, "r") as f:
            users = json.load(f)
    else:
        users = []

    users.append(entry)

    with open(rlusers_path, "w") as f:
        json.dump(users, f, indent=2)

    return entry

# hypixel

def hy_get_stats(data):
    raw = data["player"]["stats"]["Bedwars"]
    wins = raw["wins_bedwars"]
    losses = raw["losses_bedwars"]
    winrate = wins / losses if losses > 0 else wins
    stats = {
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
    }

    return stats

def hy_fetch_data(user, team):
    try:
        safe_user = quote(user)
        uuid_url = f"https://api.mojang.com/users/profiles/minecraft/{safe_user}"
        uuid_response = requests.get(uuid_url)
        uuid = uuid_response.json()["id"]
        hy_url = f"https://api.hypixel.net/v2/player?uuid={uuid}"
        headers = {
            "API-Key": hypixel_api,
        }
        data = requests.get(hy_url, headers=headers).json()
        stats = hy_get_stats(data)

        entry = {
            "team": team,
            "username": user,
            "uuid": uuid,
            "avatar": f"https://mc-heads.net/avatar/{uuid}",
            "stats": stats,
        }
        return entry
    except requests.exceptions.RequestException as e:
        return {"error": f"Could not reach Mojang/Hypixel API: {e}"}
    except KeyError as e:
        return {"error": f"Unexpected response shape, missing field: {e}"}
    except Exception as e:
        return {"error": f"Hypixel lookup failed: {e}"}

def hy_save_data(user, team, hyusers_path="hy_users.json"):
    entry = hy_fetch_data(user, team)

    if "error" in entry:
        return entry

    if os.path.exists(hyusers_path):
        with open(hyusers_path, "r") as f:
            hyusers = json.load(f)
    else:
        hyusers = []

    hyusers.append(entry)

    with open(hyusers_path, "w") as f:
        json.dump(hyusers, f, indent=2)
    
    return entry

# league of legends

def lol_get_stats(data):
    segments = data["data"]["segments"]
    stats = {}

    for seg in segments:
        if seg["type"] == "playlist" and seg["metadata"]["name"] == "Ranked Solo":
            stats = seg["stats"]["tier"]
    
    return stats

def lol_fetch_data(user, team):
    try:
        opgg = OPGG()
        results = opgg.search(user, Region.NA)
        entry = results[0].model_dump(mode="json")
        entry["team"] = team
        return entry
    except IndexError:
        return {"error": f"No League of Legends player found for '{user}'"}
    except Exception as e:
        return {"error": f"League of Legends lookup failed: {e}"}

def lol_save_data(user, team, lolusers_path="lol_users.json"):
    entry = lol_fetch_data(user, team)

    if "error" in entry:
        return entry

    if os.path.exists(lolusers_path):
        with open(lolusers_path) as f:
            lolusers = json.load(f)
    else:
        lolusers = []
    
    lolusers.append(entry)

    with open(lolusers_path, "w") as f:
        json.dump(lolusers, f, indent=2)

    return entry

# marvel rivals

def get_main_role(data):
    segments = data["data"]["segments"]
    main_role = {}

    for seg in segments:
        if seg["type"] == "hero-role":
            main_role[seg["metadata"]["name"]] = seg["stats"]["matchesPlayed"]["value"]

    return max(main_role, key=main_role.get)

def mr_get_peak(data):
    segments = data["data"]["segments"]

    for seg in segments:
        if seg["type"] == "ranked-peaks":
            peak = seg["stats"]["lifetimePeakRanked"]
    return peak

def mr_get_current(data):
    segments = data["data"]["segments"]

    for seg in segments:
        if seg["type"] == "overview":
            current = seg["stats"]["ranked"]
    return current

def mr_fetch_data(user, team):
    try:
        safe_user = quote(user)
        url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{safe_user}"
        scraper = cloudscraper.create_scraper()
        data = scraper.get(url).json()
        pi = data["data"]["platformInfo"]
        peak_rank = mr_get_peak(data)
        current_rank = mr_get_current(data)
        main_role = get_main_role(data)

        entry = {
            "team": team,
            "username": user,
            "avatar": pi["avatarUrl"],
            "peakRank": peak_rank["value"],
            "peakMetadata": {
                "iconUrl": peak_rank["metadata"]["iconUrl"],
                "tierShortName": peak_rank["metadata"]["tierShortName"],
                "seasonShortName": peak_rank["metadata"]["seasonShortName"],
            },
            "currentRank": {
                "value": current_rank["value"],
                "iconUrl": current_rank["metadata"]["iconUrl"],
                "tierShortName": current_rank["metadata"]["tierShortName"],
            },
            "mainRole": main_role,
        }
        return entry
    except requests.exceptions.RequestException as e:
        return {"error": f"Could not reach Marvel Rivals API: {e}"}
    except KeyError as e:
        return {"error": f"Unexpected response shape, missing field: {e}"}
    except Exception as e:
        return {"error": f"Marvel Rivals lookup failed: {e}"}

def mr_save_data(user, team, mrusers_path="mr_users.json"):
    entry = mr_fetch_data(user, team)

    if "error" in entry:
        return entry

    if os.path.exists(mrusers_path):
        with open(mrusers_path) as f:
            mrusers = json.load(f)
    else:
        mrusers = []
    
    mrusers.append(entry)

    with open(mrusers_path, "w") as f:
        json.dump(mrusers, f, indent=2)
    
    return entry