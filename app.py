import os
import secrets
import json
from fastapi import FastAPI, Request, Form, Depends, dependencies, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from main import get_creds, add_map, eval_submission, get_osu_ident, import_teams, find_team, recompute
from datetime import datetime
from typing import List
from starlette.middleware.sessions import SessionMiddleware
from tracker import steam, epic, xbox


app = FastAPI()
templates = Jinja2Templates(directory="templates")
osu_client = get_creds()
app.mount("/files", StaticFiles(directory="replays"), name="files")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=os.environ["SESSION_SECRET"], max_age=2592000)

osu_ids = {17805659}

class NotAuthorized(Exception):
    pass

@app.exception_handler(NotAuthorized)
def handle_unauthorized(request: Request, exc: NotAuthorized):
    return RedirectResponse("/login")

def require_auth(request: Request):
    if not request.session.get("user_id"):
        raise NotAuthorized()
    return request.session["user_id"]
@app.get("/auth/callback")
def auth_callback(request: Request, code: str, state: str):
    if state != request.session.get("oauth_state"):
        return {"error": "state mismatch"}, 400

    identity = get_osu_ident(code, "http://127.0.0.1:8000/auth/callback")

    if identity["id"] not in osu_ids:
        return {"error": "unauthorized"}, 400

    request.session["user_id"] = identity["id"]
    request.session["username"] = identity["username"]

    return RedirectResponse("/pool")

def format_ts(value):
    dt = datetime.fromisoformat(value)
    return dt.strftime("%Y-%m-%d %H:%M:%S") + " UTC+0"

templates.env.filters["fmt_ts"] = format_ts

@app.get("/player-data")

@app.get("/login")
def login(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state

    params = {
        "client_id": os.getenv("CLIENT_ID"),
        "redirect_uri": "http://127.0.0.1:8000/auth/callback",
        "response_type": "code",
        "scope": "identify",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"https://osu.ppy.sh/oauth/authorize?{query}")

@app.get("/", dependencies=[Depends(require_auth)])
def home(request):
        return templates.TemplateResponse("dash.html")

# pool

@app.get("/pool", dependencies=[Depends(require_auth)])
def view_pool(request: Request):
    with open("pool.json") as f:
        pool = json.load(f)

    search = request.query_params.get("search", "").lower()
    filter_df = request.query_params.get("filter_df", "")
    filter_wk = request.query_params.get("filter_wk", "")
    sort_keys = request.query_params.getlist("sort")

    if search: 
        pool = [
            e for e in pool
            if search in str(e["map_id"]).lower()
            or search in e["artist"].lower()
            or search in e["title"].lower()
            or search in e["difficulty"].lower()
        ]
    
    if filter_df:
        pool = [e for e in pool if str(e["df"]) == filter_df]
    
    if filter_wk:
        pool = [e for e in pool if str(e["wk"]) == filter_wk]

    for key in reversed(sort_keys):
        field = {"sr": "stars", "df": "df", "wk": "wk"}[key]
        pool.sort(key=lambda e: e[field])

    return templates.TemplateResponse(request, "pool.html", {"pool": pool})

@app.get("/settings", dependencies=[Depends(require_auth)])
def view_settings(request):
    return templates.TemplateResponse("settings.html")

@app.post("/settings/recompute", dependencies=[Depends(require_auth)])
def recompute_pool():
    count = recompute()
    return RedirectResponse(f"/settings?recomputed={count}", status_code=303)

@app.post("/pool/add", dependencies=[Depends(require_auth)])
def add_bmap(beatmap_id: int = Form(...), df: int = Form(...), wk: int = Form(...)):
    with open("pool.json") as f:
        pool = json.load(f)

    existing = False

    for entry in pool:
        if entry["map_id"] == beatmap_id:
            existing = True

    if existing:
        return RedirectResponse(url="/pool", status_code=303)

    add_map(osu_client, beatmap_id, df, wk)
    return RedirectResponse(url="/pool", status_code=303)

@app.post("/pool/toggle", dependencies=[Depends(require_auth)])
def toggle_release(checksum: str = Form(...)):
    with open("pool.json") as f:
        pool = json.load(f)

    for entry in pool:
        if entry["checksum"] == checksum:
            entry["active"] = not entry["active"]
    
    with open("pool.json", "w") as f:
        json.dump(pool, f, indent=2)
    return RedirectResponse(url="/pool", status_code=303)


@app.post("/pool/remove", dependencies=[Depends(require_auth)])
def remove_bmap(checksum: str = Form(...)):
    with open("pool.json") as f:
        pool = json.load(f)

    pool = [entry for entry in pool if entry["checksum"] != checksum]

    with open("pool.json", "w") as f:
        json.dump(pool, f, indent=2)

    return RedirectResponse(url="/pool", status_code=303)

#submission

@app.get("/submissions", dependencies=[Depends(require_auth)])
def view_submissions(request: Request):
    with open("pool.json") as f:
        pool = json.load(f)
    with open("submissions.json") as f:
        submissions = json.load(f)

    status_meta = {
        "close_diff": {"label": "INC.DIFF", "css_class": "inc-diff"},
        "close_artist": {"label": "INC. SONG", "css_class": "inc-song"},
        "incorrect": {"label": "INC. MAPSET", "css_class": "inc-ms"},
    }

    grouped = []
    for entry in pool:

        matches = [
            {**s, "team": find_team(s.get("player_id"))}
            for s in submissions
            if s["tier"] == "correct" and s["match"]["checksum"] == entry["checksum"]
        ]
        grouped.append({"map": entry, "submissions": matches})

    incorrect = []
    for s in submissions:
        if s["tier"] != "correct":
            meta = status_meta.get(s["tier"], {"label": s["tier"], "css_class": "inc-other"})
            incorrect.append({
                **s,
                "status_label": meta["label"],
                "status_class": meta["css_class"],
                "team": find_team(s.get("player_id")),
            })

    return templates.TemplateResponse(request, "submissions.html", {"grouped": grouped, "incorrect": incorrect})

#team management

@app.get("/teams", dependencies=[Depends(require_auth)])
def view_teams(request: Request):
    teams = {}
    if os.path.exists("teams.json"):
        with open("teams.json") as f:
            teams = json.load(f)
    return templates.TemplateResponse(request, "teams.html", {"teams": teams})

@app.post("/teams/import", dependencies=[Depends(require_auth)])
async def upload_teams(file: UploadFile = File(...)):
    contents = await file.read()
    with open("teams_upload.csv", "wb") as f:
        f.write(contents)

    import_teams("teams_upload.csv")
    return RedirectResponse("/teams", status_code=303)

@app.post("/teams/add", dependencies=[Depends(require_auth)])
def add_team(team_name: str = Form(...)):
    teams = {}
    if os.path.exists("teams.json"):
        with open("teams.json") as f:
            teams = json.load(f)

    teams.setdefault(team_name, [])

    with open("teams.json", "w") as f:
        json.dump(teams, f, indent=2)

    return RedirectResponse("/teams", status_code=303)

@app.post("/teams/{team_name}/save", dependencies=[Depends(require_auth)])
def save_team(
        team_name: str,
        discord_id: List[str] = Form(...),
        osu_id: List[str] = Form(...),
        osu_username: List[str] = Form(...),
):
    with open("teams.json") as f:
        teams = json.load(f)

    teams[team_name] = [
        {"discord_id": d, "osu_id": o, "osu_username": u}
        for d, o, u in zip(discord_id, osu_id, osu_username)
        if d.strip()
    ]

    with open("teams.json", "w") as f:
        json.dump(teams, f, indent=2)

    return RedirectResponse("/teams", status_code=303)

@app.post("/teams/{team_name}/remove_member", dependencies=[Depends(require_auth)])
def remove_member(team_name: str, discord_id: str = Form(...)):
    with open("teams.json") as f:
        teams = json.load(f)

    teams[team_name] = [m for m in teams[team_name] if m["discord_id"] != discord_id]

    with open("teams.json", "w") as f:
        json.dump(teams, f, indent=2)

    return RedirectResponse("/teams", status_code=303)

@app.post("/teams/{team_name}/remove", dependencies=[Depends(require_auth)])
def remove_team(team_name: str):
    with open("teams.json") as f:
        teams = json.load(f)

    teams.pop(team_name, None)

    with open("teams.json", "w") as f:
        json.dump(teams, f, indent=2)

    return RedirectResponse("/teams", status_code=303)



