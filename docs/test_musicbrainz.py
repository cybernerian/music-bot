"""
Quick sanity check — connects to the MusicBrainz Docker database
and prints 10 random recordings from a randomly chosen genre tag.

Run:
    python3 test_musicbrainz.py

Prerequisites:
    pip install psycopg2-binary
    MusicBrainz Docker must be running (see DOCKER_SETUP.md)
"""

import random
import psycopg2

MUSICBRAINZ_DB = {
    "host": "localhost",
    "port": 5432,
    "dbname": "musicbrainz_db",
    "user": "musicbrainz",
    "password": "musicbrainz",
}

SAMPLE_GENRES = [
    "rock", "pop", "jazz", "hip-hop", "electronic",
    "classical", "metal", "blues", "reggae", "folk",
    "r&b", "country", "soul", "punk", "indie",
]


class MusicBrainzTester:
    def __init__(self):
        self.conn = None

    def connect(self):
        print("Connecting to MusicBrainz Docker database...")
        self.conn = psycopg2.connect(**MUSICBRAINZ_DB)
        print("Connected.\n")

    def fetch_random_songs_by_genre(self, genre: str, limit: int = 10) -> list[dict]:
        query = """
            SELECT
                r.name        AS title,
                ac.name       AS artist,
                t.name        AS genre
            FROM recording r
            JOIN artist_credit ac ON ac.id = r.artist_credit
            JOIN recording_tag  rt ON rt.recording = r.id
            JOIN tag            t  ON t.id = rt.tag
            WHERE LOWER(t.name) = LOWER(%s)
              AND rt.count > 0
            ORDER BY RANDOM()
            LIMIT %s;
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (genre, limit))
            rows = cur.fetchall()
            return [{"title": row[0], "artist": row[1], "genre": row[2]} for row in rows]

    def run(self):
        self.connect()

        genre = random.choice(SAMPLE_GENRES)
        print(f"Randomly selected genre: {genre}")
        print("-" * 50)

        songs = self.fetch_random_songs_by_genre(genre)

        if not songs:
            print(f"No recordings found for genre '{genre}'.")
            print("Try re-running or check that the full database finished loading correctly.")
        else:
            for i, song in enumerate(songs, 1):
                print(f"{i:2}. {song['title']} — {song['artist']}")

        self.conn.close()


if __name__ == "__main__":
    MusicBrainzTester().run()
