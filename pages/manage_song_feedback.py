import os
import streamlit as st
from song_feedback_db import get_feedback, delete_feedback
from dotenv import load_dotenv
from styles import apply_styles

load_dotenv()

st.set_page_config(
    page_title="Manage Feedback – Music Bot",
    page_icon="🎵",
    layout="centered"
)
apply_styles()

username = os.getenv("LASTFM_USERNAME")

st.title("Your Feedback")
st.markdown("Manually remove entries if needed.")
st.divider()

if "selected_entry" not in st.session_state:
    st.session_state.selected_entry = None

if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = False

entries = get_feedback(username)

if not entries:
    st.markdown("No feedback recorded yet.")
else:
    for entry in entries:
        entry_id = entry["id"]
        label = f"**{entry['artist']}** — {entry['title']}  |  *{entry['rating']}*"
        is_selected = st.session_state.selected_entry == entry_id

        col_label, col_trash = st.columns([8, 1])

        with col_label:
            if st.button(label, key=f"entry_{entry_id}", use_container_width=True,
                         type="primary" if is_selected else "secondary"):
                if is_selected:
                    st.session_state.selected_entry = None
                    st.session_state.confirm_delete = False
                else:
                    st.session_state.selected_entry = entry_id
                    st.session_state.confirm_delete = False
                st.rerun()

        with col_trash:
            if st.button("🗑", key=f"trash_{entry_id}", disabled=not is_selected):
                st.session_state.confirm_delete = True
                st.rerun()

    if st.session_state.confirm_delete and st.session_state.selected_entry:
        st.divider()
        st.warning("Are you sure you want to delete this entry?")
        col_yes, col_no = st.columns([1, 1])
        with col_yes:
            if st.button("Yes, delete", use_container_width=True):
                delete_feedback(st.session_state.selected_entry)
                st.session_state.selected_entry = None
                st.session_state.confirm_delete = False
                st.toast("Entry deleted.")
                st.rerun()
        with col_no:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_delete = False
                st.rerun()

st.divider()
if st.button("← Back to Recommendations"):
    st.switch_page("pages/lastfm_song_recommendations.py")
