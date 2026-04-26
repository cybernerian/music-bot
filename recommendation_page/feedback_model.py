import numpy as np
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity

RATING_WEIGHTS = {
    "loved": 2.0,
    "liked": 1.0,
    "neutral": 0.1,
    "disliked": -1.0,
    "hated": -2.0,
}

MIN_FEEDBACK = 3


def _get_artist_tags(network, artist_name: str, limit: int = 10) -> list:
    try:
        artist = network.get_artist(artist_name)
        tags = artist.get_top_tags(limit=limit)
        return [t.item.name.strip().lower() for t in tags]
    except Exception:
        return []


def build_user_profile(feedback_records: list, network) -> dict:
    #Builds a content-based user preference profile from feedback.

    # Fetches Last.fm tags for each unique artist in the feedback, then builds a weighted preference vector
    # Returns a dict with pref_vector, tag_index, and artist_scores

    if len(feedback_records) < MIN_FEEDBACK:
        return {}

    # Fetch tags for each unique artist (one API call per artist)
    artist_tags_map = {}
    for record in feedback_records:
        artist = record["artist"]
        if artist not in artist_tags_map:
            artist_tags_map[artist] = _get_artist_tags(network, artist)

    vocab = sorted({tag for tags in artist_tags_map.values() for tag in tags})
    if not vocab:
        return {}

    tag_index = {tag: i for i, tag in enumerate(vocab)}

    pref_vector = np.zeros(len(vocab))
    total_weight = 0.0

    for record in feedback_records:
        weight = RATING_WEIGHTS.get(record["rating"], 0.0)
        if weight == 0:
            continue
        vec = np.zeros(len(vocab))
        for tag in artist_tags_map.get(record["artist"], []):
            if tag in tag_index:
                vec[tag_index[tag]] = 1.0
        pref_vector += weight * vec
        total_weight += abs(weight)

    if total_weight > 0:
        pref_vector /= total_weight

    artist_scores = defaultdict(float)
    for record in feedback_records:
        weight = RATING_WEIGHTS.get(record["rating"], 0.0)
        artist_scores[record["artist"].strip().lower()] += weight

    return {
        "pref_vector": pref_vector,
        "tag_index": tag_index,
        "artist_scores": dict(artist_scores),
    }


def personalization_multiplier(artist_name: str, artist_tags: list, user_profile: dict) -> float:
    # Return a score multiplier in [0.1, 3.0] for a candidate track. Higher means more likely to be recommended.
    # Combines cosine similarity between the candidate's tag vector and the user preference vector 
    if not user_profile:
        return 1.0

    pref_vector = user_profile.get("pref_vector")
    tag_index = user_profile.get("tag_index", {})
    artist_scores = user_profile.get("artist_scores", {})

    if pref_vector is None or np.linalg.norm(pref_vector) < 1e-9:
        return 1.0

    # Tag-based signal via cosine similarity
    candidate_vec = np.zeros(len(pref_vector))
    for tag in artist_tags:
        if tag in tag_index:
            candidate_vec[tag_index[tag]] = 1.0

    tag_signal = 0.0
    if np.linalg.norm(candidate_vec) > 1e-9:
        tag_signal = float(
            cosine_similarity(candidate_vec.reshape(1, -1), pref_vector.reshape(1, -1))[0][0]
        )

    # Direct artist signal, clamped to [-1, 1]
    raw_direct = artist_scores.get(artist_name.strip().lower(), 0.0)
    direct_signal = max(-1.0, min(1.0, raw_direct / 2.0))

    combined = tag_signal * 0.7 + direct_signal * 0.3
    multiplier = 1.0 + combined * 2.0  # range roughly [-1, 3] before clamp
    return max(0.1, min(3.0, multiplier))
