import os
import random
from collections import defaultdict
from dotenv import load_dotenv
import pylast
from recommendation_page.feedback_model import personalization_multiplier

#Baseline music recommendation system using Last.fm similarity API

def normalize_key(artist: str, title: str) -> str:
    return f"{artist.strip().lower()}::{title.strip().lower()}"


def get_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise SystemExit(f"Missing {name} in .env")
    return val


def build_network() -> pylast.LastFMNetwork:
    load_dotenv(override=True)
    return pylast.LastFMNetwork(api_key=get_env("LASTFM_API_KEY"))


def get_top_tracks(user: pylast.User, limit: int = 10, period: str = "overall"):
    # returns user's top tracks as a list of Track objects 
    top = user.get_top_tracks(limit=limit, period=period)

    results = []
    for item, _weight in top:
        track = item.item if hasattr(item, "item") else item
        results.append(track)
    return results


def build_seeds(user: pylast.User) -> list:
    # 50% recent (7day) — 5 seeds
    recent = get_top_tracks(user, limit=5, period="7day")

    # 30% all-time (overall) — 3 seeds, deduplicated against recent
    recent_keys = {normalize_key(t.artist.name, t.title) for t in recent}
    overall = [
        t for t in get_top_tracks(user, limit=10, period="overall")
        if normalize_key(t.artist.name, t.title) not in recent_keys
    ][:3]

    # 15% artist-level — 1 seed: top track from a similar artist
    artist_seed = []
    try:
        top_artists = user.get_top_artists(limit=5)
        artist = random.choice(top_artists).item if top_artists else None
        if artist:
            similar_artists = artist.get_similar(limit=10)
            picked = random.choice(similar_artists).item if similar_artists else None
            if picked:
                artist_tracks = picked.get_top_tracks(limit=5)
                if artist_tracks:
                    artist_seed = [artist_tracks[0].item]
    except Exception:
        pass

    # 5% wildcard — 1 seed: random track from ranks 10-30 overall
    wildcard = []
    try:
        deep = get_top_tracks(user, limit=30, period="overall")
        pool = [t for t in deep[10:] if normalize_key(t.artist.name, t.title) not in recent_keys]
        if pool:
            wildcard = [random.choice(pool)]
    except Exception:
        pass

    return recent + overall + artist_seed + wildcard


def get_listened_set(user: pylast.User) -> set:
    listened = set()
    for period in ("overall", "7day", "1month", "3month", "6month", "12month"):
        try:
            for t in get_top_tracks(user, limit=50, period=period):
                listened.add(normalize_key(t.artist.name, t.title))
        except Exception:
            continue
    try:
        for item in user.get_recent_tracks(limit=200):
            t = item.track
            listened.add(normalize_key(t.artist.name, t.title))
    except Exception:
        pass
    return listened


BIG_ARTIST_THRESHOLD = 1_000_000  # listeners


def _artist_listeners(artist) -> int:
    try:
        return int(artist.get_listener_count())
    except Exception:
        return 0


def _artist_top_tags(artist) -> list:
    try:
        tags = artist.get_top_tags(limit=10)
        return [t.item.name.strip().lower() for t in tags]
    except Exception:
        return []


def _artist_top_track_keys(artist) -> list:
    # returns ordered list of normalized keys for the artist's top 10 tracks
    try:
        top = artist.get_top_tracks(limit=10)
        return [normalize_key(t.item.artist.name, t.item.title) for t in top]
    except Exception:
        return []


def _score_multiplier(big_artist: bool, track_rank: int) -> float:
    # track_rank: 0-2 = top 3 (popular), 3-6 = mid, 7-9 = deep cut, -1 = not in top 10
    if big_artist:
        if track_rank in (0, 1, 2):
            return 0.55  # mega-hit from big artist — penalize
        if track_rank in (3, 4, 5, 6):
            return 1.2   # mid-tier from big artist
        return 1.5       # deep cut from big artist — prioritize
    else:
        if track_rank in (0, 1, 2):
            return 1.7   # best-known from small artist — stronger discovery push
        if track_rank in (3, 4, 5, 6):
            return 1.4   # mid-tier from small artist
        return 1.2       # deep cut from small artist — slight discovery boost

# FROM SONGS LAST FM RECOMMEND GET THERE GENRE TAGS
# SEE `fetch_candidates_by_tags()` FO RHOW THERE USED
def extract_tags_from_seeds(seeds: list) -> list[str]:
    # Collect tags from each seed track's artist, deduplicated
    seen = set()
    tags = []
    for track in seeds:
        for tag in _artist_top_tags(track.artist):
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tags


def recommend_from_similar(top_tracks, per_seed: int = 10, out_k: int = 10, listened: set = None, user_profile: dict = None):
    if listened is None:
        listened = set()
    for tr in top_tracks:
        listened.add(normalize_key(tr.artist.name, tr.title))

    scores = defaultdict(float)
    track_objs = {}
    artist_cache = {}  # artist_name -> {"listeners": int, "top_keys": list}

    for seed_track in top_tracks:
        try:
            similar = seed_track.get_similar(limit=per_seed)
        except Exception:
            continue

        for sim_track, sim_score in similar:
            key = normalize_key(sim_track.artist.name, sim_track.title)
            if key in listened:
                continue

            try:
                s = float(sim_score)
            except Exception:
                s = 0.0

            artist_name = sim_track.artist.name
            if artist_name not in artist_cache:
                artist_cache[artist_name] = {
                    "listeners": _artist_listeners(sim_track.artist),
                    "top_keys": _artist_top_track_keys(sim_track.artist),
                    "tags": _artist_top_tags(sim_track.artist),
                }

            cached = artist_cache[artist_name]
            big_artist = cached["listeners"] >= BIG_ARTIST_THRESHOLD
            top_keys = cached["top_keys"]
            track_rank = top_keys.index(key) if key in top_keys else -1

            s *= _score_multiplier(big_artist, track_rank)
            if user_profile:
                s *= personalization_multiplier(artist_name, cached["tags"], user_profile)

            scores[key] += s
            track_objs[key] = sim_track

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:out_k]
    return [track_objs[k] for k, _ in ranked]


def main():
    network = build_network()
    username = get_env("LASTFM_USERNAME")
    user = network.get_user(username)

    top_tracks = get_top_tracks(user, limit=10, period="overall")
    if not top_tracks:
        print("No top tracks found.")
        return

    print("\nCommonly played tracks:")
    for tr in top_tracks:
        print(f"- {tr.artist.name} — {tr.title}")

    recs = recommend_from_similar(top_tracks, per_seed=10, out_k=10)
    if not recs:
        print("\nNo recommendations found.")
        return

    print("\nRecommended tracks:")
    for i, tr in enumerate(recs, start=1):
        print(f"{i:02d}. {tr.artist.name} — {tr.title}")


if __name__ == "__main__":
    main()
