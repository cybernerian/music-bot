import os
from datetime import datetime, timedelta
import pandas as pd
import altair as alt
import streamlit as st
from dotenv import load_dotenv
from song_feedback_db import init_db, get_all_feedback_over_time
from styles import apply_styles, lg

load_dotenv()
init_db()

st.set_page_config(
    page_title="Music Bot Progress",
    page_icon="📈",
    layout="centered"
)
apply_styles()

username = os.getenv("LASTFM_USERNAME")

st.title("Music Bot Progress")
st.markdown(f"Tracking how {lg('Music Bot')}'s recommendations improve over time based on your feedback.", unsafe_allow_html=True)
st.divider()

RATING_ORDER = ["loved", "liked", "neutral", "disliked", "hated"]
RATING_COLOR = {"loved": "#5c8fe0", "liked": "#5cb85c", "neutral": "#aaaaaa", "disliked": "#e09a5c", "hated": "#e05c5c"}

PERIOD_OPTIONS  = ["Week", "Month", "Year", "All Time"]
SOURCE_OPTIONS  = ["Music Bot", "Last.fm", "All"]
SOURCE_FILTER   = {"Music Bot": "musicbrainz", "Last.fm": "lastfm", "All": None}
SOURCE_LABEL    = {"Music Bot": "Music Bot", "Last.fm": "Last.fm", "All": "Music Bot & Last.fm"}

records = get_all_feedback_over_time(username)

if not records:
    st.markdown("No feedback recorded yet. Head to the Recommendations page and rate some songs!")
else:
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["created_at"])
    df["source label"] = df["source"].map({"lastfm": "Last.fm", "musicbrainz": "Music Bot"})

    # Dropdowns
    col_period, col_source = st.columns(2)
    with col_period:
        period = st.selectbox("Period", PERIOD_OPTIONS, index=0)
    with col_source:
        source = st.selectbox("Source", SOURCE_OPTIONS, index=0)

    # Filter by source
    source_key = SOURCE_FILTER[source]
    filtered = df[df["source"] == source_key].copy() if source_key else df.copy()

    # Filter by time period
    now = datetime.now()
    if period == "Week":
        filtered = filtered[filtered["date"] >= now - timedelta(weeks=1)]
    elif period == "Month":
        filtered = filtered[filtered["date"] >= now - timedelta(days=30)]
    elif period == "Year":
        filtered = filtered[filtered["date"] >= now - timedelta(days=365)]

    # Group label based on period
    if period == "Week":
        filtered["group"] = filtered["date"].dt.strftime("%a %b %d")
        filtered["sort_key"] = filtered["date"].dt.floor("D")
        x_title = "Day"
    elif period == "Month":
        filtered["group"] = filtered["date"].dt.to_period("W").apply(lambda r: r.start_time.strftime("%b %d"))
        filtered["sort_key"] = filtered["date"].dt.to_period("W").apply(lambda r: r.start_time)
        x_title = "Week"
    elif period == "Year":
        filtered["group"] = filtered["date"].dt.strftime("%b %Y")
        filtered["sort_key"] = filtered["date"].dt.to_period("M").apply(lambda r: r.start_time)
        x_title = "Month"
    else:  # All Time
        filtered["group"] = filtered["date"].dt.strftime("%b %Y")
        filtered["sort_key"] = filtered["date"].dt.to_period("M").apply(lambda r: r.start_time)
        x_title = "Month"

    chart_title = f"Ratings per {period} ({SOURCE_LABEL[source]})"
    st.markdown(f"**{len(filtered)} ratings recorded**")
    st.divider()

    if filtered.empty:
        st.markdown("No ratings found for this filter. Try a different period or source.")
    else:
        sort_map = filtered[["group", "sort_key"]].drop_duplicates().set_index("group")["sort_key"].to_dict()
        sorted_groups = sorted(sort_map, key=lambda g: sort_map[g])

        bar_df = (
            filtered.groupby(["group", "sort_key", "rating"])
            .size()
            .reset_index(name="count")
            .sort_values("sort_key")
        )

        bars = alt.Chart(bar_df).mark_bar().encode(
            x=alt.X("group:N", title=x_title, sort=sorted_groups, axis=alt.Axis(labelAngle=-30)),
            y=alt.Y("count:Q", title="Number of Ratings", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("rating:N",
                            scale=alt.Scale(domain=RATING_ORDER, range=[RATING_COLOR[r] for r in RATING_ORDER]),
                            legend=alt.Legend(title="Rating"),
                            sort=RATING_ORDER),
            order=alt.Order("rating:N", sort="ascending"),
            tooltip=[
                alt.Tooltip("group:N", title=x_title),
                alt.Tooltip("rating:N", title="Rating"),
                alt.Tooltip("count:Q", title="Count"),
            ]
        )

        st.altair_chart(bars.properties(
            title=chart_title,
            height=380,
            padding={"left": 10, "right": 10, "top": 20, "bottom": 10}
        ).configure_view(
            strokeWidth=1,
            stroke="#333333"
        ), use_container_width=True)

        st.caption("Taller green bars over time = recommendations improving.")

        st.divider()

        st.markdown("**Rating breakdown**")
        counts = filtered["rating"].value_counts().reindex(RATING_ORDER, fill_value=0)
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Loved", counts["loved"])
        col2.metric("Liked", counts["liked"])
        col3.metric("Neutral", counts["neutral"])
        col4.metric("Disliked", counts["disliked"])
        col5.metric("Hated", counts["hated"])

st.divider()
if st.button("← Back to Recommendations"):
    st.switch_page("pages/lastfm_song_recommendations.py")
