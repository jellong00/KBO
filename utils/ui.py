from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

PLOTLY_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "responsive": True,
}


def setup_page(title: str, icon: str = "⚾") -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px;}
        [data-testid="stMetric"] {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(128,128,128,0.22);
            border-radius: 14px;
            padding: 14px 16px;
        }
        [data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,128,0.18);}
        h1, h2, h3 {letter-spacing: -0.02em;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def modernize(fig: go.Figure, title: str | None = None, height: int = 480) -> go.Figure:
    fig.update_layout(
        title=title,
        height=height,
        margin=dict(l=20, r=20, t=60 if title else 25, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Arial, Apple SD Gothic Neo, Malgun Gothic, sans-serif", size=13),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    return fig


def global_filters(df, key_prefix: str = "global"):
    min_year, max_year = int(df["year"].min()), int(df["year"].max())
    years = st.sidebar.slider(
        "연도 범위",
        min_year,
        max_year,
        (min_year, max_year),
        key=f"{key_prefix}_years",
    )
    team_options = sorted(df["team"].dropna().astype(str).unique().tolist())
    teams = st.sidebar.multiselect(
        "구단",
        team_options,
        default=team_options,
        key=f"{key_prefix}_teams",
    )
    return years, teams
