import os
from dotenv import load_dotenv
import pylast

load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
USERNAME = os.getenv("LASTFM_USERNAME")

if not API_KEY or not USERNAME:
    raise SystemExit("Missing LASTFM_API_KEY or LASTFM_USERNAME in .env")

network = pylast.LastFMNetwork(api_key=API_KEY)
user = network.get_user(USERNAME)

top_tracks = user.get_top_tracks(period="overall", limit=1)

if not top_tracks:
    print("No top tracks found (is your account new / private?)")
else:
    top = top_tracks[0]          # pylast.TopItem
    track = top.item             # pylast.Track
    playcount = top.weight       # usually playcount

    print("Most scrobbled track (overall):")
    print(f"{track.artist.name} — {track.title}")
    print(f"Plays: {playcount}")