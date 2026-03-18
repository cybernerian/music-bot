import os
import streamlit as st
from baseline_model import build_network, get_top_tracks, recommend_from_similar
from db import init_db, save_feedback, get_feedback_summary
from dotenv import load_dotenv

load_dotenv()
init_db()

st.set_page_config(
    page_title="Recommendations – Music Recommender",
    page_icon="🎵",
    layout="centered"
)

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
    </style>
""", unsafe_allow_html=True)

username = os.getenv("LASTFM_USERNAME")

st.title(":green[Recommendations]")
st.markdown(f"Personalized picks for :orange[{username}].")
st.divider()

# Store recommendations in session state
if "recs" not in st.session_state:
    st.session_state.recs = []

if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = {}

# Fetch recommendations on page load
if not st.session_state.recs:
    with st.spinner("Finding recommendations..."):
        network = build_network()
        user = network.get_user(username)
        top_tracks = get_top_tracks(user, limit=5, period="overall")
        raw_recs = recommend_from_similar(top_tracks, per_seed=5, out_k=5)

    st.session_state.recs = [
        {"artist": tr.artist.name, "title": tr.title}
        for tr in raw_recs
    ]
    st.session_state.feedback_given = {}

# Display recommendations
if st.session_state.recs:
    st.title(":green[Recommended Songs]")
    st.caption("Provide feedback to improve future recommenadtions!")

    for i, rec in enumerate(st.session_state.recs, start=1):
        artist = rec["artist"]
        title = rec["title"]
        key = f"{artist}::{title}"

        col_label, col_like, col_dislike = st.columns([6, 1, 1])

        with col_label:
            st.markdown(f"{i}. :orange[**{artist}**] — :orange[{title}]")

        current = st.session_state.feedback_given.get(key)

        with col_like:
            if current == "liked":
                st.markdown("✅")
            else:
                if st.button("👍", key=f"like_{key}"):
                    save_feedback(username, artist, title, liked=True)
                    st.session_state.feedback_given[key] = "liked"
                    st.rerun()

        with col_dislike:
            if current == "disliked":
                st.markdown("❌")
            else:
                if st.button("👎", key=f"dislike_{key}"):
                    save_feedback(username, artist, title, liked=False)
                    st.session_state.feedback_given[key] = "disliked"
                    st.rerun()

    # Feedback summary
    summary = get_feedback_summary(username)
    total = summary["liked"] + summary["disliked"]
    if total > 0:
        st.divider()
        st.markdown(
            f"**Total feedback recorded:** "
            f":green[{summary['liked']} 👍] · "
            f":red[{summary['disliked']} 👎] "
            f"({total} total)"
        )
        st.caption(
            "This feedback will be used to improve future recommendations. Thank you!"
        )

# Back button
st.divider()
if st.button("← Back"):
    st.session_state.recs = []
    st.switch_page("app.py")