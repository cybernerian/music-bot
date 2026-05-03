import streamlit as st

# Color palette — mirrors config.toml for reference
DARK_GREEN = "#53af4a"
LIGHT_GREEN = "#9ff058"

def apply_styles():
    st.markdown("""
        <style>
            @font-face {
                font-family: 'Consolas';
                src: url('/app/static/consolas.woff') format('woff');
                font-weight: 400;
                font-style: normal;
            }
            @font-face {
                font-family: 'Consolas';
                src: url('/app/static/consolas-bold.woff') format('woff');
                font-weight: 700;
                font-style: normal;
            }
            @font-face {
                font-family: 'triplicate-c3';
                src: url('/app/static/triplicate-c3.ttf') format('truetype');
                font-weight: 400;
                font-style: normal;
            }
            @font-face {
                font-family: 'triplicate-c3';
                src: url('/app/static/triplicate-c3-bold.ttf') format('truetype');
                font-weight: 700;
                font-style: normal;
            }
            html, body, .stApp, p, li, a, span, label, input, textarea, button, code, pre, .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span, .stMarkdown a, .stMarkdown strong, .stMarkdown em, div[data-testid="stMarkdownContainer"] p, div[data-testid="stMarkdownContainer"] li, div[data-testid="stMarkdownContainer"] span, div[data-testid="stMarkdownContainer"] a, div[data-testid="stMarkdownContainer"] strong, div[data-testid="stMarkdownContainer"] em {
                font-family: 'triplicate-c3', monospace !important;
                font-size: 1.00rem !important;
            }
            table, th, td, thead, tbody, tr {
                font-family: 'triplicate-c3', monospace !important;
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: 'Consolas', monospace !important;
                font-weight: 700 !important;
                color: #9ff058 !important;
            }
            div[data-testid="stButton"] > button {
                background: rgba(255, 255, 255, 0.02) !important;
                border: 1px solid rgba(255, 255, 255, 0.22) !important;
                color: #f2f2f2 !important;
                border-radius: 6px !important;
                box-shadow: none !important;
                font-family: 'triplicate-c3', monospace !important;
                min-height: 2.4rem !important;
                height: auto !important;
                padding: 0.35rem 0.75rem !important;
                transition: border-color 120ms ease, background 120ms ease, color 120ms ease;
            }
            div[data-testid="stButton"] > button:hover {
                background: rgba(159, 240, 88, 0.06) !important;
                border-color: rgba(159, 240, 88, 0.75) !important;
                color: #9ff058 !important;
            }
            div[data-testid="stButton"] > button:focus,
            div[data-testid="stButton"] > button:active {
                box-shadow: 0 0 0 1px rgba(159, 240, 88, 0.28) !important;
            }
            div[data-testid="stButton"] > button[kind="primary"] {
                background: rgba(159, 240, 88, 0.08) !important;
                border-color: rgba(159, 240, 88, 0.9) !important;
                color: #9ff058 !important;
            }
            div[data-testid="stButton"] > button p {
                white-space: normal !important;
                overflow-wrap: anywhere !important;
                word-break: break-word !important;
                line-height: 1.25 !important;
            }
        </style>
    """, unsafe_allow_html=True)


def dg(text, bold=False):
    """Wrap text in dark green (#53af4a)."""
    inner = f"<b>{text}</b>" if bold else text
    return f"<span style='color:{DARK_GREEN}'>{inner}</span>"


def lg(text, bold=False):
    """Wrap text in light green (#9ff058)."""
    inner = f"<b>{text}</b>" if bold else text
    return f"<span style='color:{LIGHT_GREEN}'>{inner}</span>"
