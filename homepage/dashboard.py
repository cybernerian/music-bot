# lastfm_client.py

import os
from dotenv import load_dotenv
import pylast

# Load environment variables
load_dotenv()

def get_network():
    api_key = os.getenv("LASTFM_API_KEY")
    if not api_key:
        raise RuntimeError("LASTFM_API_KEY not found in .env file.")
    
    return pylast.LastFMNetwork(api_key=api_key)


def get_recent_tracks(username: str, limit: int = 5):
    """
    Returns a list of the user's most recent tracks.
    Each track is returned as a dictionary:
    {
        "artist": str,
        "title": str,
        "album": str or None
    }
    """
    network = get_network()
    user = network.get_user(username)

    recent = user.get_recent_tracks(limit=limit)

    tracks = []
    for item in recent:
        track = item.track

        album_title = None
        try:
            album = track.get_album()
            if album:
                album_title = album.title
        except:
            pass

        tracks.append({
            "artist": track.artist.name,
            "title": track.title,
            "album": album_title
        })

    return tracks

def get_top_tracks_week(username: str, limit: int = 3):
    """
    Returns top tracks for the last 7 days.
    Each item:
    { "artist": str, "title": str, "playcount": int }
    """
    network = get_network()
    user = network.get_user(username)

    top = user.get_top_tracks(limit=limit, period="7day")

    results = []
    for item in top:
        # pylast returns TopItem objects with .item and .weight
        track_obj = item.item
        playcount = int(item.weight) if str(item.weight).isdigit() else item.weight

        results.append({
            "artist": track_obj.artist.name,
            "title": track_obj.title,
            "playcount": playcount
        })

    return results


def get_top_genre_week(username: str, sample_tracks: int = 10):
    """
    Approximates "top genre" for the last 7 days by:
    1) Taking top tracks from last 7 days (sample_tracks)
    2) Fetching Last.fm top tags for each track
    3) Counting tag frequency
    Returns:
      { "genre": str, "count": int } or None
    """
    network = get_network()
    user = network.get_user(username)

    top = user.get_top_tracks(limit=sample_tracks, period="7day")

    tag_counts = {}

    for item in top:
        track_obj = item.item
        try:
            tags = track_obj.get_top_tags(limit=5)
        except Exception:
            continue

        for tag_item in tags:
            try:
                tag_name = tag_item.item.name.lower().strip()
            except Exception:
                continue

            tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1

    if not tag_counts:
        return None

    top_tag, count = max(tag_counts.items(), key=lambda x: x[1])
    return {"genre": top_tag, "count": count}