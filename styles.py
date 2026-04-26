import streamlit as st

# Color palette — mirrors config.toml for reference
DARK_GREEN = "#53af4a"
LIGHT_GREEN = "#9ff058"

def apply_styles():
    st.markdown("""
        <style>
            @font-face {
                font-family: 'arnold-bocklin';
                src: url('/app/static/arnold-bocklin.ttf') format('truetype');
            }
            @font-face {
                font-family: 'vipnagorgialla-rg';
                src: url('/app/static/vipnagorgialla-rg.otf') format('opentype');
            }
            html, body, [class*="css"] {
                font-family: 'vipnagorgialla-rg', sans-serif !important;
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: 'arnold-bocklin', sans-serif !important;
                color: #9ff058 !important;
            }
            button p { white-space: nowrap !important; }
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
