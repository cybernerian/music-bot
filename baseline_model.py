import os
from collections import defaultdict
from dotenv import load_dotenv
import pylast

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


def recommend_from_similar(top_tracks, per_seed: int = 10, out_k: int = 10):
    #tracks reccomended based on similar tracks to the user's top tracks.
    listened = set()
    for tr in top_tracks:
        listened.add(normalize_key(tr.artist.name, tr.title))

    scores = defaultdict(float)
    track_objs = {}

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