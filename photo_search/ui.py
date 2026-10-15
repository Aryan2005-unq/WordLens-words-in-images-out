"""Shared visual styling for the Streamlit pages."""

import streamlit as st


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --ink: #f3f4fb; --muted: #a5acc0; --accent: #8b83ff; }
        .stApp { background: radial-gradient(ellipse at top left, #20243a 0%, #151821 48%, #111318 100%); }
        [data-testid="stHeader"] { background: rgba(17,19,24,.78); }
        [data-testid="stSidebar"] { background: #171a23; border-right: 1px solid #2b3040; }
        [data-testid="stSidebarNav"] { padding-top: 1rem; }
        .block-container { max-width: 1240px; padding-top: 2rem; padding-bottom: 3rem; }
        h1, h2, h3 { color: var(--ink); letter-spacing: -.025em; }
        h1 { font-weight: 750; }
        p, label, [data-testid="stCaptionContainer"] { color: #c1c6d4; }
        [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(30,34,46,.88); border: 1px solid #343a4b;
            border-radius: 18px; box-shadow: 0 12px 32px rgba(0,0,0,.22);
        }
        [data-testid="stForm"] { padding: 1rem 1.25rem; }
        div.stButton > button, div.stFormSubmitButton > button {
            border-radius: 11px; border: 0; background: #7169ef; color: white;
            font-weight: 650; padding: .55rem 1.1rem;
        }
        div.stButton > button:hover, div.stFormSubmitButton > button:hover {
            background: #8982ff; color: white; border: 0;
        }
        [data-testid="stTextInput"] input, [data-testid="stDateInput"] input {
            border-radius: 10px; background: #202431; color: #f3f4fb;
        }
        [data-testid="stSelectbox"] div, [data-testid="stMultiSelect"] div { border-color: #3a4052; }
        [data-testid="stImage"] img { border-radius: 14px; }
        [data-testid="stAlert"] { border-radius: 12px; background: #202534; }
        hr { border-color: #343a4b; }
        </style>
        """,
        unsafe_allow_html=True,
    )
