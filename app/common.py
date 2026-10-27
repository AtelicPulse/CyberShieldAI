"""Shared page setup. Every page must import this module first, because it puts the project root on sys.path."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # pyright: ignore[reportMissingImports]  # noqa: E402

from config import config as cfg  # noqa: E402
from core import db  # noqa: E402
from core.simulation import ReplayStream, new_state  # noqa: E402


def page_setup(title, show_title=True, show_disclaimer=True):
    st.set_page_config(page_title=f"Cyber Shield AI - {title}", layout="wide")
    db.init_db()
    if show_disclaimer:
        st.warning(cfg.DISCLAIMER)   # shown on every page on purpose
    if show_title:
        st.title(title)

    # Inject sidebar navigation styling matching the reference navigation mockup
    st.markdown(
        """
        <style>
        /* Sidebar background */
        [data-testid="stSidebar"] {
            background-color: #0b0f17 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        }

        /* Sidebar navigation section header: NAVIGATION */
        [data-testid="stSidebarNav"]::before {
            content: "NAVIGATION";
            display: block;
            padding: 1.25rem 1.25rem 0.5rem 1.25rem;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            color: #64748b;
            text-transform: uppercase;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* Navigation items */
        [data-testid="stSidebarNavLink"] {
            border-radius: 8px !important;
            margin: 4px 10px !important;
            padding: 9px 14px !important;
            font-weight: 500 !important;
            font-size: 0.88rem !important;
            color: #94a3b8 !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
            border-left: 4px solid transparent !important;
        }

        [data-testid="stSidebarNavLink"]:hover {
            background: rgba(255, 255, 255, 0.05) !important;
            color: #f1f5f9 !important;
            transform: translateX(2px);
        }

        /* Active navigation link with vertical left accent bar matching the reference */
        [data-testid="stSidebarNavLink"][aria-current="page"] {
            background: rgba(16, 185, 129, 0.12) !important;
            color: #34d399 !important;
            font-weight: 700 !important;
            border-left: 4px solid #10b981 !important;
            box-shadow: 0 2px 10px rgba(16, 185, 129, 0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("**REST API:** [localhost:8000/docs](http://localhost:8000/docs)")
    st.sidebar.caption("Run run_api.sh in a second terminal to enable it.")
    st.sidebar.caption(f"Model: {cfg.MODEL_NAME}")


@st.cache_resource
def replay_holdout():
    # one shared, read-only copy; the row number in this order is the alert's flow_row
    from core.simulation import load_holdout
    return load_holdout()


def get_session():
    ss = st.session_state
    if "stream" not in ss:
        ss.stream = ReplayStream(replay_holdout())
        ss.state = new_state()
        ss.run_id = db.start_run(cfg.MODEL_NAME, "dashboard replay")
        ss.running = False
        ss.recent = []
    return ss


def reset_session():
    for key in ("stream", "state", "run_id", "running", "recent"):
        st.session_state.pop(key, None)
