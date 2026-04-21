import os
import random
import streamlit as st
from recommendation_page.lastfm_similarity_model import build_network, build_seeds, get_listened_set, recommend_from_similar
from recommendation_page.feedback_model import build_user_profile
from song_feedback_db import init_db, save_feedback, get_feedback, get_feedback_summary
from dotenv import load_dotenv
from styles import apply_styles, dg, lg

load_dotenv()
init_db()

st.set_page_config(
    page_title="Recommendations – Music Bot",
    page_icon="🎵",
    layout="centered"
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

if not st.session_state.recs:
    with st.spinner("Finding recommendations..."):
        pool, personalized = fetch_rec_pool(username)
        raw_recs = random.sample(pool, min(3, len(pool)))

    st.session_state.recs = raw_recs
    st.session_state.personalized = personalized
    st.session_state.feedback_given = {}

# Display recommendations
if st.session_state.recs:
    st.title("Recommended Songs")
    if st.session_state.get("personalized"):
        st.markdown(f"Personalized using your Last.fm history {lg('**and**')} your feedback.", unsafe_allow_html=True)
    else:
        st.markdown("Based on your Last.fm listening history. Provide feedback to personalize future recommendations!")
    st.markdown("Provide feedback to improve future recommendations!")

    for i, rec in enumerate(st.session_state.recs, start=1):
        artist = rec["artist"]
        title = rec["title"]
        key = f"{artist}::{title}"

        col_label, col_love, col_like, col_dislike, col_hate = st.columns([4, 1, 1, 1.1, 1])

        with col_label:
            st.markdown(f"{i}. {dg(artist, bold=True)} — {dg(title)}", unsafe_allow_html=True)

        current = st.session_state.feedback_given.get(key)

        with col_love:
            if st.button("Love", key=f"love_{key}", type="primary" if current == "loved" else "secondary"):
                if current != "loved":
                    save_feedback(username, artist, title, rating="loved")
                    st.session_state.feedback_given[key] = "loved"
                    st.session_state.pending_toast = f'"{title}" added to loved list'
                    st.rerun()

        with col_like:
            if st.button("Like", key=f"like_{key}", type="primary" if current == "liked" else "secondary"):
                if current != "liked":
                    save_feedback(username, artist, title, rating="liked")
                    st.session_state.feedback_given[key] = "liked"
                    st.session_state.pending_toast = f'"{title}" added to liked list'
                    st.rerun()

        with col_dislike:
            if st.button("Dislike", key=f"dislike_{key}", type="primary" if current == "disliked" else "secondary"):
                if current != "disliked":
                    save_feedback(username, artist, title, rating="disliked")
                    st.session_state.feedback_given[key] = "disliked"
                    st.session_state.pending_toast = f'"{title}" added to disliked list'
                    st.rerun()

        with col_hate:
            if st.button("Hate", key=f"hate_{key}", type="primary" if current == "hated" else "secondary"):
                if current != "hated":
                    save_feedback(username, artist, title, rating="hated")
                    st.session_state.feedback_given[key] = "hated"
                    st.session_state.pending_toast = f'"{title}" added to hated list'
                    st.rerun()

    # Music Bot placeholder
    st.divider()
    st.title("Music Bot")
    st.markdown(
        "In addition to your Last.fm listening history, your feedback from recommended songs is also included. "
        "The more feedback you give, the more Music Bot will improve."
    )

    if st.button("View feedback you gave"):
        st.switch_page("pages/manage_song_feedback.py")

    # Feedback summary
    summary = get_feedback_summary(username)
    total = summary["liked"] + summary["disliked"]
    if total > 0:
        st.divider()
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
        st.switch_page("app.py")
with col_refresh:
    if st.button("Refresh Recommendations", use_container_width=True):
        st.session_state.recs = []
        st.session_state.feedback_given = {}
        st.rerun()
