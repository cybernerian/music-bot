import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5533),
        dbname=os.getenv("DB_NAME", "music_bot"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    title TEXT NOT NULL,
                    rating TEXT NOT NULL CHECK (rating IN ('loved', 'liked', 'neutral', 'disliked', 'hated')),
                    source TEXT NOT NULL DEFAULT 'lastfm',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # migrations
            cur.execute("ALTER TABLE feedback ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'lastfm';")
            cur.execute("ALTER TABLE feedback DROP CONSTRAINT IF EXISTS feedback_rating_check;")
            cur.execute("ALTER TABLE feedback ADD CONSTRAINT feedback_rating_check CHECK (rating IN ('loved', 'liked', 'neutral', 'disliked', 'hated'));")

        conn.commit()


def save_feedback(username: str, artist: str, title: str, rating: str, source: str = "lastfm"):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO feedback (username, artist, title, rating, source)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (username, artist, title, rating, source))
        conn.commit()


def get_feedback(username: str) -> list:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, artist, title, rating, source, created_at FROM feedback
                WHERE username = %s
                ORDER BY created_at DESC
            """, (username,))
            rows = cur.fetchall()
    return [{"id": r[0], "artist": r[1], "title": r[2], "rating": r[3], "source": r[4], "created_at": r[5]} for r in rows]


def delete_feedback(entry_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feedback WHERE id = %s", (entry_id,))
        conn.commit()


def get_all_feedback_over_time(username: str) -> list:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT artist, title, rating, source, created_at
                FROM feedback
                WHERE username = %s
                ORDER BY created_at ASC
            """, (username,))
            rows = cur.fetchall()
    return [{"artist": r[0], "title": r[1], "rating": r[2], "source": r[3], "created_at": r[4]} for r in rows]


def get_feedback_summary(username: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT rating, COUNT(*) FROM feedback
                WHERE username = %s
                GROUP BY rating
            """, (username,))
            rows = cur.fetchall()

    counts = {"loved": 0, "liked": 0, "disliked": 0, "hated": 0}
    for rating, count in rows:
        counts[rating] = count
    counts["liked"] = counts["loved"] + counts["liked"]
    counts["disliked"] = counts["disliked"] + counts["hated"]
    return counts
