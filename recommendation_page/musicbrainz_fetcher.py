import os
import psycopg2
from dotenv import load_dotenv
from recommendation_page.feedback_model import personalization_multiplier
from recommendation_page.lastfm_similarity_model import extract_tags_from_seeds

load_dotenv()

MUSICBRAINZ_DB = {
    "host": os.getenv("MB_HOST", "localhost"),
    "port": int(os.getenv("MB_PORT", 5432)),
    "dbname": os.getenv("MB_DB", "musicbrainz_db"),
    "user": os.getenv("MB_USER", "musicbrainz"),
    "password": os.getenv("MB_PASSWORD", "musicbrainz"),
}


def _get_conn():
    return psycopg2.connect(**MUSICBRAINZ_DB)


def _normalize(s: str) -> str:
    return s.strip().lower()

# FROM LAST TAGS SURFACE SONGS THAT ARE SIMILAR
# e.g ROCK TAG FROM LAST WILL SURFACE ROCK SONGS
def fetch_candidates_by_tags(tags: list[str], limit: int = 50, listened: set = None) -> list[dict]:
    """
    Query MusicBrainz for recordings matching any of the given tags.
    Returns: [{"artist": str, "title": str, "tags": list[str]}, ...]
    Filters out songs already in the listened set.
    """
    if listened is None:
        listened = set()
    if not tags:
        return []

    normalized_tags = [_normalize(t) for t in tags]
    placeholders = ",".join(["%s"] * len(normalized_tags))

    # Over-fetch to account for listened filtering downstream
    # DISTINCT and ORDER BY RANDOM() can't be in the same SELECT in PostgreSQL — use subquery
    candidate_query = f"""
        SELECT id, title, artist FROM (
            SELECT DISTINCT r.id, r.name AS title, ac.name AS artist
            FROM recording r
            JOIN artist_credit ac ON ac.id = r.artist_credit
            JOIN recording_tag rt ON rt.recording = r.id
            JOIN tag t ON t.id = rt.tag
            WHERE LOWER(t.name) IN ({placeholders})
              AND rt.count > 0
        ) sub
        ORDER BY RANDOM()
        LIMIT %s;
    """

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(candidate_query, normalized_tags + [limit * 3])
            rows = cur.fetchall()

            if not rows:
                return []

            # Filter listened songs and collect recording IDs for tag batch fetch
            candidates = []
            recording_ids = []
            for rec_id, title, artist in rows:
                key = f"{_normalize(artist)}::{_normalize(title)}"
                if key not in listened:
                    candidates.append({"id": rec_id, "title": title, "artist": artist, "tags": []})
                    recording_ids.append(rec_id)

            if not candidates:
                return []

            # Batch fetch all tags for the shortlisted candidates in one query
            tag_placeholders = ",".join(["%s"] * len(recording_ids))
            cur.execute(
                f"""
                SELECT rt.recording, t.name
                FROM recording_tag rt
                JOIN tag t ON t.id = rt.tag
                WHERE rt.recording IN ({tag_placeholders})
                  AND rt.count > 0;
                """,
                recording_ids,
            )
            tag_rows = cur.fetchall()

    # Map tags back to each candidate
    tags_by_id: dict[int, list[str]] = {}
    for rec_id, tag_name in tag_rows:
        tags_by_id.setdefault(rec_id, []).append(_normalize(tag_name))

    for c in candidates:
        c["tags"] = tags_by_id.get(c["id"], [])

    result = [{"artist": c["artist"], "title": c["title"], "tags": c["tags"]} for c in candidates]
    return result[:limit]


def recommend_from_musicbrainz(seeds, out_k: int = 10, listened: set = None, user_profile: dict = None) -> list[dict]:
    if listened is None:
        listened = set()

    # Step 1: get genre tags from the user's Last.fm seeds
    tags = extract_tags_from_seeds(seeds)
    if not tags:
        return []

    # Step 2: fetch candidates from MusicBrainz that match those tags
    candidates = fetch_candidates_by_tags(tags, limit=50, listened=listened)
    if not candidates:
        return []

    # Step 3: score each candidate against the user's feedback profile
    scored = []
    for candidate in candidates:
        score = 1.0
        if user_profile:
            score = personalization_multiplier(candidate["artist"], candidate["tags"], user_profile)
        scored.append((score, candidate))

    # Step 4: sort by score, return top N
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"artist": c["artist"], "title": c["title"]} for _, c in scored[:out_k]]
