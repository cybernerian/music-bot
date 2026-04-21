import os
import streamlit as st

from homepage.dashboard import get_recent_tracks, get_top_tracks_week, get_top_genre_week
from dotenv import load_dotenv
from styles import apply_styles, dg, lg

load_dotenv()

st.set_page_config(
    page_title="Music Bot",
    page_icon="🎵",
    layout="centered"
)
apply_styles()

username = os.getenv("LASTFM_USERNAME")
st.title("Music Bot")
st.markdown(
    f"Welcome, {lg(username)}! Here's your personalized music dashboard.",
    unsafe_allow_html=True,
)
st.divider()

@st.cache_data(ttl=10800)  # 3 hours
def cached_recent_tracks(username):
    return get_recent_tracks(username, limit=5)

st.title("5 Most Recent Songs", anchor="recent-songs")

recent_tracks = cached_recent_tracks(username)
if recent_tracks:
    for i, track in enumerate(recent_tracks, start=1):
        st.markdown(
            f"{i}. {dg(track['artist'], bold=True)} — {dg(track['title'])}",
            unsafe_allow_html=True,
        )
else:
    st.write("No recent tracks found.")
st.divider()

@st.cache_data(ttl=10800)  # 3 hours
def cached_weekly_top(username):
    return get_top_tracks_week(username, limit=3)

st.title("Top 3 Songs This Week", anchor="weekly-top")

weekly_top = cached_weekly_top(username)
if weekly_top:
    for i, track in enumerate(weekly_top, start=1):
        st.markdown(
            f"{i}. {dg(track['artist'], bold=True)} — {dg(track['title'])} ({track['playcount']} plays)",
            unsafe_allow_html=True,
        )
else:
    st.write("No weekly top tracks found.")
st.divider()

@st.cache_data(ttl=10800)  # 3 hours
def cached_top_genre(username):
    return get_top_genre_week(username)

st.title("Top Genre This Week", anchor="weekly-genre")

top_genre = cached_top_genre(username)
if top_genre:
    st.markdown(
        f"Top genre: {lg(top_genre['genre'], bold=True)}",
        unsafe_allow_html=True,
    )
else:
    st.write("No top genre found.")

if st.button("Get Recommendations"):
    st.switch_page("pages/lastfm_song_recommendations.py")
