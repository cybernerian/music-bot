# Music Recommender

## What This Project Does

A machine learning music recommendation system that integrates with Last.fm to discover new songs based on your listening habits. The app uses a Streamlit UI to display your music data and generate personalized song recommendations.

**Core Features:**
- **Dashboard**: Displays your Last.fm profile data — recent songs, weekly top tracks, and top genre
- **Recommendation Engine**: ML model generates song recommendations tailored to your listening patterns by fetching candidates from the MusicBrainz database
- **Feedback Loop**: Like/dislike recommendations, which feeds into the model's weighting system for future predictions
- **Learning**: The model improves over time as it learns from your feedback on recommendations

**Tech Stack:**
- Frontend: Streamlit
- ML Model: Python with scikit-learn, pandas, numpy
- Libraries: pylast (Last.fm API), scikit-learn (similarity calculations)
- Databases: PostgreSQL (user data & feedback), MusicBrainz (song metadata)
- Data Sources: Last.fm API, user feedback

## ML Model Approach

**Content-Based Filtering** — Recommends songs similar to ones the user likes based on song metadata.

**Why this approach:**
- Works well with structured metadata (genre, artist, tags from MusicBrainz)
- Integrates naturally with the 70/30 weighting + preference table
- Improves as user feedback accumulates in PostgreSQL
- Simple and interpretable — can explain why a song was recommended
- No cold-start problem for new users

**Implementation:**
- Convert song metadata into feature vectors
- Use cosine similarity (scikit-learn) to compare user's liked songs against MusicBrainz candidates
- Rank candidates by similarity scores
- Adjust rankings based on 70/30 weighting and preference weightage from PostgreSQL
- Return top-ranked song as recommendation

## Build Roadmap

**Phase 1 (current):** Stateless rule-based recommendations using the 70/30 weighting system. Fetches listening history from Last.fm, queries MusicBrainz for matching candidates, filters out already-heard songs, and returns a recommendation. No data is stored — it re-reads from Last.fm and MusicBrainz fresh each time.

**Phase 2:** Add a separate PostgreSQL database (`music_recommender`) to store user feedback (liked/disliked songs). This preference data layers on top of the 70/30 system to re-rank candidates, turning it into a proper content-based ML model that improves over time.

## Database Setup

Two separate databases are used:
- **MusicBrainz** — runs in Docker, stores song metadata. See [DOCKER_SETUP.md](./DOCKER_SETUP.md)
- **music_recommender** — runs in Postgres.app on port `5533`, stores user feedback/preferences (Phase 2)

## How It Works

### Data Sources

- **Last.fm API**: Provides user's listening history (recent tracks, weekly top tracks, genres)
- **PostgreSQL**: Stores user feedback (liked/disliked recommendations) and preference weightage
- **MusicBrainz**: Song metadata repository used to find similar songs

### Recommendation Engine: Two Weighting Systems

1. **Listening History Weighting (70/30)**
   - 70% weight on user's recent listening (last 7 days)
   - 30% weight on user's all-time listening history
   - Pulled from Last.fm API

2. **Preference Weightage (from user feedback)**
   - Stored in PostgreSQL preference table
   - Built from songs user has liked/disliked on previous recommendations
   - Extracts metadata (genre, artist, similar artists) to influence future recommendations
   - Works independently from the 70/30 weighting

### How the Model Generates a Recommendation

1. **Fetch Listening History from Last.fm**
   - Get user's recent tracks (7 days) and all-time top tracks
   - Apply 70/30 weighting to determine focus areas (genres, artists)

2. **Load Preference Weightage from PostgreSQL**
   - Retrieve user's liked/disliked song metadata from preference table
   - This tells the model which genres/artists/styles to boost or avoid

3. **Query MusicBrainz Database**
   - Search for similar songs matching the weighted criteria
   - Use combined signals: (70/30 listening history) + (preference weights)
   - Search includes genre matches, artist similarities, related artists

4. **Filter & Rank Candidates**
   - Exclude songs user has already listened to (from Last.fm history)
   - Rank candidates by relevance to both weighting systems
   - Return top-ranked song as the recommendation

### Feedback Loop (User Improves the Model)

1. User sees a recommendation and clicks like/dislike
2. Extract song metadata (genre, artist, related info)
3. Store in PostgreSQL preference table with weightage
4. Next recommendation uses updated preference table to influence results
