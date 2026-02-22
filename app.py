import os
from dotenv import load_dotenv
import pylast

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
if not API_KEY:
    raise SystemExit("Missing LASTFM_API_KEY in .env")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

network = pylast.LastFMNetwork(api_key=API_KEY)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/top-track", response_class=HTMLResponse)
async def top_track(request: Request, username: str = Form(...)):
    username = username.strip()

    try:
        user = network.get_user(username)
        top_tracks = user.get_top_tracks(period="overall", limit=1)

        if not top_tracks:
            result = "No top tracks found (new/private account?)."
        else:
            top = top_tracks[0]
            track = top.item
            plays = top.weight
            result = f"{track.artist.name} — {track.title} (Plays: {plays})"

    except pylast.WSError as e:
        result = f"Last.fm error: {e}"
    except Exception as e:
        result = f"Unexpected error: {e}"

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "result": result, "username": username},
    )