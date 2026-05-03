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

CANDIDATE_FETCH_LIMIT = 250
FETCH_OVERSAMPLE_MULTIPLIER = 8


def _get_conn():
    return psycopg2.connect(**MUSICBRAINZ_DB)


def _normalize(s: str) -> str:
    return s.strip().lower()


def _norm_list(xs):
    nums = [x for x in xs if x is not None]
    if not nums:
        return [0.0 for _ in xs]
    mn, mx = min(nums), max(nums)
    if mx == mn:
        return [1.0 if (x is not None and x > 0) else 0.0 for x in xs]
    return [(x - mn) / (mx - mn) if x is not None else 0.0 for x in xs]


def _artist_type_bonus(artist_type: str | None) -> float:
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


# Shared artist tags subquery used in all three candidate sources
_ARTIST_TAGS_SUBQUERY = """
    LEFT JOIN (
        SELECT art_tag.artist,
               array_agg(LOWER(tag.name) ORDER BY art_tag.count DESC) AS artist_tags
        FROM artist_tag art_tag
        JOIN tag ON tag.id = art_tag.tag
        WHERE art_tag.count > 0
        GROUP BY art_tag.artist
    ) artagg ON artagg.artist = a.id
"""

_SELECT_COLS = """
    r.id, r.name AS title, ac.name AS artist,
    r.length AS length_ms, NULL::numeric AS rec_rating,
    at2.name AS artist_type,
    COALESCE(artagg.artist_tags, ARRAY[]::text[]) AS artist_tags
"""


def _query_by_recording_tags(cur, tags: list[str], fetch_limit: int):
    """Source 1: recordings directly tagged with seed genres."""
    placeholders = ",".join(["%s"] * len(tags))
    cur.execute(f"""
        SELECT id, title, artist, length_ms, rec_rating, artist_type, artist_tags FROM (
            SELECT DISTINCT {_SELECT_COLS}
            FROM recording r
            JOIN artist_credit ac ON ac.id = r.artist_credit
            LEFT JOIN artist_credit_name acn ON acn.artist_credit = ac.id
            LEFT JOIN artist a ON a.id = acn.artist
            LEFT JOIN artist_type at2 ON at2.id = a.type
            JOIN recording_tag rt ON rt.recording = r.id
            JOIN tag t ON t.id = rt.tag
            {_ARTIST_TAGS_SUBQUERY}
            WHERE LOWER(t.name) IN ({placeholders})
              AND rt.count > 0
        ) sub
        ORDER BY RANDOM()
        LIMIT %s;
    """, tags + [fetch_limit])
    return cur.fetchall()


def _query_by_artist_tags(cur, tags: list[str], fetch_limit: int):
    """Source 2: recordings from artists tagged with seed genres (catches untagged recordings)."""
    placeholders = ",".join(["%s"] * len(tags))
    cur.execute(f"""
        SELECT id, title, artist, length_ms, rec_rating, artist_type, artist_tags FROM (
            SELECT DISTINCT {_SELECT_COLS}
            FROM recording r
            JOIN artist_credit ac ON ac.id = r.artist_credit
            JOIN artist_credit_name acn ON acn.artist_credit = ac.id
            JOIN artist a ON a.id = acn.artist
            LEFT JOIN artist_type at2 ON at2.id = a.type
            JOIN artist_tag art_tag ON art_tag.artist = a.id
            JOIN tag t ON t.id = art_tag.tag
            {_ARTIST_TAGS_SUBQUERY}
            WHERE LOWER(t.name) IN ({placeholders})
              AND art_tag.count > 0
        ) sub
        ORDER BY RANDOM()
        LIMIT %s;
    """, tags + [fetch_limit])
    return cur.fetchall()


def _query_by_similar_artists(cur, seed_artist_names: list[str], fetch_limit: int):
    """Source 3: recordings from artists MusicBrainz marks as similar to the seed artists."""
    if not seed_artist_names:
        return []
    placeholders = ",".join(["%s"] * len(seed_artist_names))
    cur.execute(f"""
        WITH seed_artists AS (
            SELECT DISTINCT a.id
            FROM artist a
            WHERE LOWER(a.name) IN ({placeholders})
        ),
        similar_artists AS (
            SELECT DISTINCT
                CASE WHEN laa.entity0 IN (SELECT id FROM seed_artists)
                     THEN laa.entity1 ELSE laa.entity0 END AS artist_id
            FROM l_artist_artist laa
            JOIN link l ON l.id = laa.link
            JOIN link_type lt ON lt.id = l.link_type
            WHERE lt.name = 'similar artist'
              AND (laa.entity0 IN (SELECT id FROM seed_artists)
                   OR laa.entity1 IN (SELECT id FROM seed_artists))
        )
        SELECT id, title, artist, length_ms, rec_rating, artist_type, artist_tags FROM (
            SELECT DISTINCT {_SELECT_COLS}
            FROM recording r
            JOIN artist_credit ac ON ac.id = r.artist_credit
            JOIN artist_credit_name acn ON acn.artist_credit = ac.id
            JOIN artist a ON a.id = acn.artist
            JOIN similar_artists sa ON sa.artist_id = a.id
            LEFT JOIN artist_type at2 ON at2.id = a.type
            {_ARTIST_TAGS_SUBQUERY}
        ) sub
        ORDER BY RANDOM()
        LIMIT %s;
    """, [_normalize(n) for n in seed_artist_names] + [fetch_limit])
    return cur.fetchall()


def fetch_candidates(
    tags: list[str],
    seed_artist_names: list[str],
    limit: int = 50,
    listened: set = None,
) -> list[dict]:
    """
    Pull candidates from three MusicBrainz sources, merge and deduplicate.
    Returns: [{"artist", "title", "tags", "length_ms", "artist_type", "artist_tags"}, ...]
    """
    if listened is None:
        listened = set()
    if not tags and not seed_artist_names:
        return []

    normalized_tags = [_normalize(t) for t in tags]
    fetch_limit = limit * FETCH_OVERSAMPLE_MULTIPLIER

    with _get_conn() as conn:
        with conn.cursor() as cur:
            rows_recording = _query_by_recording_tags(cur, normalized_tags, fetch_limit) if normalized_tags else []
            rows_artist    = _query_by_artist_tags(cur, normalized_tags, fetch_limit) if normalized_tags else []
            rows_similar   = _query_by_similar_artists(cur, seed_artist_names, fetch_limit)

            all_rows = rows_recording + rows_artist + rows_similar

            if not all_rows:
                return []

            # Deduplicate by recording ID, filter listened
            seen_ids = set()
            candidates = []
            recording_ids = []

            for rec_id, title, artist, length_ms, _rec_rating, artist_type, artist_tags in all_rows:
                if rec_id in seen_ids:
                    continue
                seen_ids.add(rec_id)
                key = f"{_normalize(artist)}::{_normalize(title)}"
                if key in listened:
                    continue
                candidates.append({
                    "id": rec_id,
                    "title": title,
                    "artist": artist,
                    "tags": [],
                    "length_ms": length_ms,
                    "artist_type": artist_type,
                    "artist_tags": list(artist_tags or []),
                })
                recording_ids.append(rec_id)

            if not candidates:
                return []

            # Batch fetch recording-level tags for all candidates
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

    tags_by_id: dict[int, list[str]] = {}
    for rec_id, tag_name in tag_rows:
        tags_by_id.setdefault(rec_id, []).append(_normalize(tag_name))

    for c in candidates:
        c["tags"] = tags_by_id.get(c["id"], [])

    return [
        {
            "artist":      c["artist"],
            "title":       c["title"],
            "tags":        c["tags"],
            "length_ms":   c["length_ms"],
            "artist_type": c["artist_type"],
            "artist_tags": c["artist_tags"],
        }
        for c in candidates
    ][:limit]


def recommend_from_musicbrainz(seeds, out_k: int = 10, listened: set = None, user_profile: dict = None) -> list[dict]:
    if listened is None:
        listened = set()

    tags = extract_tags_from_seeds(seeds)
    seed_artist_names = [s.artist.name for s in seeds if hasattr(s, "artist")]

    candidates = fetch_candidates(tags, seed_artist_names, limit=CANDIDATE_FETCH_LIMIT, listened=listened)
    if not candidates:
        return []

    seed_set = {_normalize(t) for t in tags}

    tag_matches, artist_strengths, lengths = [], [], []

    for c in candidates:
        tm = sum(1 for t in c.get("tags", []) if _normalize(t) in seed_set)
        tag_matches.append(tm)

        artist_strength = sum(1.0 for t in c.get("artist_tags", []) if _normalize(t) in seed_set)
        artist_strengths.append(artist_strength)

        lm = c.get("length_ms")
        lengths.append((lm / 1000.0) if lm else None)

    n_tag_matches      = _norm_list(tag_matches)
    n_artist_strengths = _norm_list(artist_strengths)

    user_mean, sigma = 180.0, 60.0
    def _length_score(s):
        if s is None or s <= 0:
            return 0.0
        return math.exp(-((s - user_mean) ** 2) / (2 * sigma ** 2))

    length_scores = [_length_score(s) for s in lengths]

    w_tags           = 0.35
    w_artist_strength = 0.30
    w_length          = 0.10

    scored = []
    for i, c in enumerate(candidates):
        base = (
            w_tags            * n_tag_matches[i]
            + w_artist_strength * n_artist_strengths[i]
            + w_length          * length_scores[i]
        )
        base *= _artist_type_bonus(c.get("artist_type"))
        if user_profile:
            base *= personalization_multiplier(c["artist"], c.get("tags", []), user_profile)
        scored.append((base, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"artist": c["artist"], "title": c["title"]} for _, c in scored[:out_k]]
