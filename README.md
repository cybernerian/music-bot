# Music Bot

A personalized music recommendation system in Python. Music Bot imports a user's Last.fm listening history, finds candidate songs in a self-hosted MusicBrainz database, and ranks them with cosine similarity against a preference vector built from user feedback.

Built by Diya Dalal and Isaiah Casias.

## How it works

1. Pylast pulls the user's listening history from Last.fm.
2. Last.fm's similar-song methods generate seed songs, and their artist tags (genre, mood, era) are extracted.
3. A local MusicBrainz PostgreSQL database (Docker) is queried for songs matching those tags, producing a randomized pool of 150 candidates.
4. Each candidate's metadata is converted into a feature vector.
5. The feedback table is converted into a weighted preference vector (loved, liked, neutral, disliked, hated).
6. scikit-learn's cosine similarity ranks the candidates against the preference vector, and the top 3 songs are returned.

## Tech stack

Python, scikit-learn, NumPy, PostgreSQL, Docker, Pylast (Last.fm API), MusicBrainz
