import os
import streamlit as st

from lastfm_client import get_recent_tracks, get_top_tracks_week, get_top_genre_week
from baseline_model import build_network, get_top_tracks, recommend_from_similar
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Page config
st.set_page_config(
    page_title="Music Recommender",
    page_icon="🎵",
    layout="centered"
)


username = os.getenv("LASTFM_USERNAME")
st.title(":green[Music Recommender]")
st.markdown(
    f"Welcome, :orange[{username}]! Here's your personalized music dashboard.",
)
st.divider()

# Call get_recent_tracks from lastfm_client.py then cache it for 3 hours to avoid too many API calls + load site faster.
@st.cache_data(ttl=10800)  # 3 hours
def cached_recent_tracks(username):
    return get_recent_tracks(username, limit=5)

st.title(":green[5 Most Recent Songs]", anchor="recent-songs")

# Loop through recent tracks and display them. If no tracks, show message.
recent_tracks = cached_recent_tracks(username)
if recent_tracks:
    for i, track in enumerate(recent_tracks, start=1):
        st.markdown(
            f"{i}. :orange[**{track['artist']}**] — :orange[{track['title']}]")
else:
    st.write("No recent tracks found.")
st.divider()

# Call get_top_tracks_week from lastfm_client.py then cache it for 3 hours to avoid too many API calls + load site faster.
@st.cache_data(ttl=10800)  # 3 hours
def cached_weekly_top(username):
    return get_top_tracks_week(username, limit=3)

st.title(":green[Top 3 Songs This Week]", anchor="weekly-top")

# Loop through weekly top tracks and display them. If no tracks, show message.
weekly_top = cached_weekly_top(username)
if weekly_top:
    for i, track in enumerate(weekly_top, start=1):
        st.markdown(
            f"{i}. :orange[**{track['artist']}**] — :orange[{track['title']}] ({track['playcount']} plays)")
else:
    st.write("No weekly top tracks found.")
st.divider()


# Call get_top_genre from lastfm_client.py then cache it for 3 hours to avoid too many API calls + load site faster.
@st.cache_data(ttl=10800)  # 3 hours (3 * 60 * 60)
def cached_top_genre(username):
    return get_top_genre_week(username)

st.title(":green[Top Genre This Week]", anchor="weekly-genre")

# Display top genre. If no genre found, show message.
top_genre = cached_top_genre(username)
if top_genre:
    st.markdown(
        f"Top genre: :orange[**{top_genre['genre']}**]")
else:
    st.write("No top genre found.")

#Display recommendations from baseline_model
st.divider()

if st.button("Get Recommendations"):
    network = build_network()
    user = network.get_user(username)

    top_tracks = get_top_tracks(user, limit=10, period="overall")
    recs = recommend_from_similar(top_tracks, per_seed=10, out_k=10)

    st.title(":green[Recommended Songs]")

    if recs:
        for i, tr in enumerate(recs, start=1):
            st.markdown(
                f"{i}. :orange[**{tr.artist.name}**] — :orange[{tr.title}]"
            )
    else:
        st.write("No recommendations found.")
