import os
import random
import streamlit as st
from recommendation_page.lastfm_similarity_model import build_network, build_seeds, get_listened_set, recommend_from_similar
from recommendation_page.feedback_model import build_user_profile
from recommendation_page.musicbrainz_fetcher import recommend_from_musicbrainz
from song_feedback_db import init_db, save_feedback, get_feedback, get_feedback_summary
from dotenv import load_dotenv
from styles import apply_styles, dg, lg

load_dotenv()
init_db()

st.set_page_config(
    page_title="Recommendations – Music Bot",
    page_icon="🎵",
    layout="wide"
)
apply_styles()

username = os.getenv("LASTFM_USERNAME")

st.title("Recommendations")
st.markdown(f"Personalized picks for {lg(username)}.", unsafe_allow_html=True)
st.divider()

# Store recommendations in session state
if "recs" not in st.session_state:
    st.session_state.recs = []

if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = {}

if "personalized" not in st.session_state:
    st.session_state.personalized = False

if "pending_toast" not in st.session_state:
    st.session_state.pending_toast = None

if st.session_state.pending_toast:
    st.toast(st.session_state.pending_toast)
    st.session_state.pending_toast = None


def _render_recommendation_table(recommendations, feedback_state_key, key_prefix, source=None):
    column_widths = [0.9, 3.0, 3.2, 1.15, 1.15, 1.25, 1.35, 1.1]
    with st.container(border=True):
        header_columns = st.columns(column_widths)
        for column, label in zip(header_columns, ["#", "Artist", "Song", "Love", "Like", "Neut", "Dis", "Hate"]):
            with column:
                st.markdown(f"**{label}**")

    for index, rec in enumerate(recommendations, start=1):
        artist = rec["artist"]
        title = rec["title"]
        feedback_key = f"{key_prefix}::{artist}::{title}"
        current = st.session_state[feedback_state_key].get(feedback_key)

        with st.container(border=True):
            row_columns = st.columns(column_widths)

            with row_columns[0]:
                st.markdown(f"**{index}**")

            with row_columns[1]:
                st.markdown(dg(artist, bold=True), unsafe_allow_html=True)

            with row_columns[2]:
                st.markdown(dg(title), unsafe_allow_html=True)

            rating_buttons = [
                ("Love", "loved", "love"),
                ("Like", "liked", "like"),
                ("Neut", "neutral", "neutral"),
                ("Dis", "disliked", "dislike"),
                ("Hate", "hated", "hate"),
            ]

            for column, (label, rating, button_suffix) in zip(row_columns[3:], rating_buttons):
                with column:
                    if st.button(
                        label,
                        key=f"{key_prefix}_{button_suffix}_{feedback_key}",
                        type="primary" if current == rating else "secondary",
                        use_container_width=True,
                    ):
                        if current != rating:
                            save_args = {"rating": rating}
                            if source is not None:
                                save_args["source"] = source
                            save_feedback(username, artist, title, **save_args)
                            st.session_state[feedback_state_key][feedback_key] = rating
                            st.session_state.pending_toast = f'"{title}" marked as {rating}'
                            st.rerun()

# @st.cache_data(ttl=86400)  # 1 day
def fetch_rec_pool(username):
    network = build_network()
    user = network.get_user(username)
    seeds = build_seeds(user)
    listened = get_listened_set(user)

    feedback_records = get_feedback(username)
    user_profile = build_user_profile(feedback_records, network)

    pool = recommend_from_similar(seeds, per_seed=10, out_k=15, listened=listened, user_profile=user_profile)
    return [{"artist": tr.artist.name, "title": tr.title} for tr in pool], bool(user_profile)

if "mb_recs" not in st.session_state:
    st.session_state.mb_recs = []

if "mb_feedback_given" not in st.session_state:
    st.session_state.mb_feedback_given = {}

# Last.fm section
st.title("Last.fm Recommendations")
st.markdown("Generate recommendations from your Last.fm listening history and then rate them.")

if st.button("Generate Last.fm Recommendations", use_container_width=True):
    with st.spinner("Finding recommendations..."):
        pool, personalized = fetch_rec_pool(username)

    if pool:
        st.session_state.recs = random.sample(pool, min(3, len(pool)))
        st.session_state.personalized = personalized
        st.session_state.feedback_given = {}
    else:
        st.session_state.recs = []
        st.session_state.personalized = False
        st.warning("No Last.fm recommendations were found right now. Try again in a moment.")

if st.session_state.recs:
    if st.session_state.get("personalized"):
        st.markdown(f"Personalized using your Last.fm history {lg('**and**')} your feedback.", unsafe_allow_html=True)
    else:
        st.markdown("Based on your Last.fm listening history. Provide feedback to personalize future recommendations!")
    st.markdown("Provide feedback to improve future recommendations!")
    _render_recommendation_table(st.session_state.recs, "feedback_given", "lastfm")

# Music Bot section
st.divider()
st.title("Music Bot")
st.markdown(
    "In addition to your Last.fm listening history, your feedback from recommended songs is also included. "
    "The more feedback you give, the more Music Bot will improve."
)

if not st.session_state.mb_recs:
    if st.button("Generate Music Bot Recommendations", use_container_width=True):
        with st.spinner("Finding Music Bot recommendations..."):
            network = build_network()
            user = network.get_user(username)
            seeds = build_seeds(user)
            listened = get_listened_set(user)
            feedback_records = get_feedback(username)
            user_profile = build_user_profile(feedback_records, network)
            st.session_state.mb_recs = recommend_from_musicbrainz(seeds, out_k=3, listened=listened, user_profile=user_profile)
            st.session_state.mb_feedback_given = {}
        st.rerun()

if st.session_state.mb_recs:
    _render_recommendation_table(st.session_state.mb_recs, "mb_feedback_given", "musicbrainz", source="musicbrainz")

st.divider()
st.subheader("Feedback Table")
st.markdown("Here you can view and or edit the feedback you gave to last fm or music bot here")

if st.button("View feedback you gave", use_container_width=True):
    st.switch_page("pages/manage_song_feedback.py")

# Feedback summary
summary = get_feedback_summary(username)
total = summary["liked"] + summary["disliked"]
if total > 0:
    st.markdown(
        f"**Total feedback recorded:** "
        f":green[{summary['liked']} liked] · "
        f":red[{summary['disliked']} disliked] "
        f"({total} total)"
    )
    st.caption(
        "This feedback will be used to improve future recommendations. Thank you!"
    )

# Back / Refresh buttons
st.divider()
col_back, col_spacer, col_refresh = st.columns([1, 1, 2])
with col_back:
    if st.button("← Back", use_container_width=True):
        st.session_state.recs = []
        st.session_state.personalized = False
        st.switch_page("app.py")
with col_refresh:
    if st.button("Refresh Recommendations", use_container_width=True):
        st.session_state.recs = []
        st.session_state.mb_recs = []
        st.session_state.personalized = False
        st.session_state.feedback_given = {}
        st.session_state.mb_feedback_given = {}
        st.rerun()
