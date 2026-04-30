import os
import math
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


def _norm_list(xs):
    # Scale numeric features to [0, 1] so the score weights stay readable.
    nums = [x for x in xs if x is not None]
    if not nums:
        return [0.0 for _ in xs]
    mn, mx = min(nums), max(nums)
    if mx == mn:
        return [1.0 if (x is not None and x > 0) else 0.0 for x in xs]
    out = []
    for x in xs:
        if x is None:
            out.append(0.0)
        else:
            out.append((x - mn) / (mx - mn))
    return out


def _artist_type_bonus(artist_type: str | None) -> float:
    # Tiny prior to keep solo artists and smaller acts slightly more visible.
    if not artist_type:
        return 1.0

    normalized = artist_type.strip().lower()
    if normalized == "person":
        return 1.08
    if normalized == "group":
        return 1.0
    if normalized in {"orchestra", "choir"}:
        return 0.95
    return 1.0


CANDIDATE_FETCH_LIMIT = 250
FETCH_OVERSAMPLE_MULTIPLIER = 8

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

    # Over-fetch hard so the post-filtering pool still stays wide enough to diversify results.
    # DISTINCT and ORDER BY RANDOM() can't be in the same SELECT in PostgreSQL — use subquery
    candidate_query = f"""
        SELECT id, title, artist, length_ms, rec_rating, artist_type, artist_tags FROM (
            -- Pull recording metadata plus pre-aggregated artist tags in one pass.
            SELECT DISTINCT r.id, r.name AS title, ac.name AS artist,
                   r.length AS length_ms, NULL::numeric AS rec_rating,
                   at.name AS artist_type,
                   COALESCE(artagg.artist_tags, ARRAY[]::text[]) AS artist_tags
            FROM recording r
            JOIN artist_credit ac ON ac.id = r.artist_credit
            LEFT JOIN artist a ON a.name = ac.name
            LEFT JOIN artist_type at ON at.id = a.type
            JOIN recording_tag rt ON rt.recording = r.id
            JOIN tag t ON t.id = rt.tag
            LEFT JOIN (
                SELECT art_tag.artist, array_agg(LOWER(tag.name) ORDER BY art_tag.count DESC) AS artist_tags
                FROM artist_tag art_tag
                JOIN tag ON tag.id = art_tag.tag
                WHERE art_tag.count > 0
                GROUP BY art_tag.artist
            ) artagg ON artagg.artist = a.id
            WHERE LOWER(t.name) IN ({placeholders})
              AND rt.count > 0
        ) sub
        ORDER BY RANDOM()
        LIMIT %s;
    """

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(candidate_query, normalized_tags + [limit * FETCH_OVERSAMPLE_MULTIPLIER])
            rows = cur.fetchall()

            if not rows:
                return []

            # Filter listened songs and collect recording IDs for tag batch fetch
            candidates = []
            recording_ids = []
            for rec_id, title, artist, length_ms, rec_rating, artist_type, artist_tags in rows:
                key = f"{_normalize(artist)}::{_normalize(title)}"
                if key not in listened:
                    candidates.append({
                        "id": rec_id,
                        "title": title,
                        "artist": artist,
                        "tags": [],
                        "length_ms": length_ms,
                        "rec_rating": rec_rating,
                        "artist_type": artist_type,
                        "artist_tags": list(artist_tags or []),
                    })
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

    result = [
        {
            "artist": c["artist"],
            "title": c["title"],
            "tags": c["tags"],
            "length_ms": c.get("length_ms"),
            "rec_rating": c.get("rec_rating"),
            "artist_type": c.get("artist_type"),
            "artist_tags": c.get("artist_tags", []),
        }
        for c in candidates
    ]
    return result[:limit]


def recommend_from_musicbrainz(seeds, out_k: int = 10, listened: set = None, user_profile: dict = None) -> list[dict]:
    if listened is None:
        listened = set()

    # Step 1: get genre tags from the user's Last.fm seeds
    tags = extract_tags_from_seeds(seeds)
    if not tags:
        return []

    # Step 2: fetch candidates from MusicBrainz that match those tags
    candidates = fetch_candidates_by_tags(tags, limit=CANDIDATE_FETCH_LIMIT, listened=listened)
    if not candidates:
        return []

    # Step 3: compute feature vectors and score each candidate
    seed_set = set([_normalize(t) for t in tags])

    tag_matches = []
    rec_strengths = []
    artist_strengths = []
    ratings = []
    lengths = []

    for c in candidates:
        # Recording tags are the closest match to the seed tags, so they stay the main signal.
        tm = sum(1 for t in c.get("tags", []) if _normalize(t) in seed_set)
        tag_matches.append(tm)
        rec_strengths.append(tm)  # proxy if rt.count not available

        # Artist tags add a broader style signal and help surface related artists.
        artist_strength = 0.0
        for tag_name in c.get("artist_tags", []):
            if _normalize(tag_name) in seed_set:
                artist_strength += 1.0
        artist_strengths.append(artist_strength)

        # Rating is optional in this DB dump, so missing values stay neutral.
        r = c.get("rec_rating")
        try:
            rnum = float(r) if r is not None else 0.0
        except Exception:
            rnum = 0.0
        ratings.append(rnum / 5.0 if rnum > 0 else 0.0)

        # length in seconds
        lm = c.get("length_ms")
        lengths.append((lm / 1000.0) if lm else None)

    # normalization helpers
    def _norm_list(xs):
        nums = [x for x in xs if x is not None]
        if not nums:
            return [0.0 for _ in xs]
        mn, mx = min(nums), max(nums)
        if mx == mn:
            return [1.0 if (x is not None and x > 0) else 0.0 for x in xs]
        out = []
        for x in xs:
            if x is None:
                out.append(0.0)
            else:
                out.append((x - mn) / (mx - mn))
        return out

    n_tag_matches = _norm_list(tag_matches)
    n_rec_strengths = _norm_list(rec_strengths)
    n_artist_strengths = _norm_list(artist_strengths)
    n_ratings = _norm_list(ratings)

    # length score: prefer near 180s (3min) with sigma 60s
    user_mean = 180.0
    sigma = 60.0
    def _length_score(s):
        if s is None or s <= 0:
            return 0.0
        return math.exp(-((s - user_mean) ** 2) / (2 * (sigma ** 2)))

    length_scores = [_length_score(s) for s in lengths]

    # Baseline weights: recording tags still matter, but they no longer dominate the ranking.
    w_tags = 0.25
    w_rec_strength = 0.08
    w_artist_strength = 0.22
    w_rating = 0.18
    w_length = 0.12

    scored = []
    for i, c in enumerate(candidates):
        base = (
            w_tags * n_tag_matches[i]
            + w_rec_strength * n_rec_strengths[i]
            + w_artist_strength * n_artist_strengths[i]
            + w_rating * n_ratings[i]
            + w_length * length_scores[i]
        )

        # Keep a small discovery bias toward less mainstream artist types.
        base *= _artist_type_bonus(c.get("artist_type"))
        # apply personalization multiplier on top if available
        if user_profile:
            base *= personalization_multiplier(c["artist"], c.get("tags", []), user_profile)
        scored.append((base, c))

    # Step 4: sort by score, return top N
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"artist": c["artist"], "title": c["title"]} for _, c in scored[:out_k]]
