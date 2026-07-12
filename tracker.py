import cloudscraper
import json
from dotenv import load_dotenv
from urllib.parse import quote
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

def rl_get_data(user, platform, team, rlusers_path="rl_users.json"):
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
        "ratings": ratings,
    }

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

def hy_get_data(user, team, hyusers_path="hy_users.json"):
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

def lol_get_data(user, team, lolusers_path="lol_users.json"):
    safe_user = quote(user)
    url = f"https://api.tracker.gg/api/v2/lol/standard/profile/ign/{safe_user}"
    scraper = cloudscraper.create_scraper()
    data = scraper.get(url).json()
    pi = data["data"]["platformInfo"]



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

def mr_get_data(user, team, mrusers_path="mr_users.json"):
    safe_user = quote(user)
    url = f"https://api.tracker.gg/api/v2/marvel-rivals/standard/profile/ign/{safe_user}"
    scraper = cloudscraper.create_scraper()
    data = scraper.get(url).json()
    pi = data["data"]["platformInfo"]
    peak_rank = mr_get_peak(data)
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
        "mainRole": main_role,
    }

    if os.path.exists(mrusers_path):
        with open(mrusers_path) as f:
            mrusers = json.load(f)
    else:
        mrusers = []
    
    mrusers.append(entry)

    with open(mrusers_path, "w") as f:
        json.dump(mrusers, f, indent=2)
    
    return entry
    


rl_get_data("76561198017084683", "steam", "autism")
hy_get_data("Wlnks", "autism")
mr_get_data("nectar", "autism")