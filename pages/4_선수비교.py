"""
pages/4_선수비교.py
---------------------
두 선수를 선택해 세이버메트릭스 + 기본 성적을 겹쳐보는 중첩 레이더 차트
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from utils.data_loader import load_data, get_years
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import STAT_GLOSSARY, render_glossary

st.set_page_config(page_title="1:1 선수 비교", page_icon="⚔️", layout="wide")

df = load_data()
years = get_years(df)

st.title("⚔️ 1:1 선수 비교 (Head-to-Head)")
render_glossary(["hit_AVG", "hit_HR", "hit_RBI", "hit_OBP", "hit_SLG", "hit_OPS",
                  "pit_ERA", "pit_WHIP", "pit_W", "pit_SV", "pit_SO", "pit_BB"])

selected_year = st.selectbox("비교 시즌 선택", options=years, index=len(years) - 1)
season_df = df[df["year"] == selected_year].copy()

batter_pool_base = season_df[season_df["hit_PA"] > 0]
pitcher_pool_base = season_df[(season_df["primary_position"] == "투수") & (season_df["pit_IP"] > 0)]

col1, col2, col3 = st.columns([2, 1, 2])

with col1:
    st.subheader("선수 A")
    pos_a = st.radio("포지션 유형 A", options=["타자", "투수"], horizontal=True, key="pos_a")
    pool_a = batter_pool_base if pos_a == "타자" else pitcher_pool_base
    player_a = st.selectbox("선수 선택 A", options=sorted(pool_a["player_name"].dropna().unique()), key="player_a")

with col3:
    st.subheader("선수 B")
    pos_b = st.radio("포지션 유형 B", options=["타자", "투수"], horizontal=True, key="pos_b")
    pool_b = batter_pool_base if pos_b == "타자" else pitcher_pool_base
    player_b = st.selectbox("선수 선택 B", options=sorted(pool_b["player_name"].dropna().unique()), key="player_b")

with col2:
    st.markdown("<div style='text-align:center; font-size:36px; padding-top:60px;'>VS</div>", unsafe_allow_html=True)

st.divider()

if pos_a != pos_b:
    st.warning("두 선수의 포지션 유형(타자/투수)이 다릅니다. 같은 유형끼리 비교할 때 레이더 차트가 더 의미 있습니다.")


def get_row(pool, name):
    rows = pool[pool["player_name"] == name]
    return rows.iloc[0] if not rows.empty else None


def build_radar_values(row, is_pitcher, cohort):
    if is_pitcher:
        axes = {
            "탈삼진율(K9)": ("pit_K9", True), "제구력(BB9↓)": ("pit_BB9", False),
            "피홈런 억제(HR9↓)": ("pit_HR9", False), "ERA↓": ("pit_ERA", False), "WHIP↓": ("pit_WHIP", False),
        }
    else:
        axes = {
            "타율": ("hit_AVG", True), "출루율": ("hit_OBP", True), "장타율": ("hit_SLG", True),
            "홈런": ("hit_HR", True), "OPS": ("hit_OPS", True),
        }
    labels, values = [], []
    for label, (col, higher_better) in axes.items():
        if col not in cohort.columns or row is None:
            continue
        s = cohort[col].dropna()
        val = row.get(col, np.nan)
        pct = 0 if (s.empty or pd.isna(val)) else (
            (s < val).sum() / len(s) * 100 if higher_better else (s > val).sum() / len(s) * 100
        )
        labels.append(label)
        values.append(round(pct, 1))
    return labels, values


row_a, row_b = get_row(pool_a, player_a), get_row(pool_b, player_b)
is_pitcher_a, is_pitcher_b = pos_a == "투수", pos_b == "투수"
cohort_a = pitcher_pool_base if is_pitcher_a else batter_pool_base
cohort_b = pitcher_pool_base if is_pitcher_b else batter_pool_base

labels_a, values_a = build_radar_values(row_a, is_pitcher_a, cohort_a)
labels_b, values_b = build_radar_values(row_b, is_pitcher_b, cohort_b)

st.subheader("🕸️ 백분위 기준 중첩 레이더 차트")

if labels_a and labels_b:
    if labels_a == labels_b:
        common_labels, va, vb = labels_a, values_a, values_b
    else:
        common_labels = labels_a
        va = values_a
        vb = values_b + [0] * (len(labels_a) - len(values_b)) if len(values_b) < len(labels_a) else values_b[:len(labels_a)]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=va + [va[0]], theta=common_labels + [common_labels[0]], fill="toself", name=player_a,
        line=dict(color=COLOR_SEQUENCE[0], width=2), fillcolor="rgba(37, 99, 235, 0.25)",
    ))
    fig.add_trace(go.Scatterpolar(
        r=vb + [vb[0]], theta=common_labels + [common_labels[0]], fill="toself", name=player_b,
        line=dict(color=COLOR_SEQUENCE[1], width=2), fillcolor="rgba(249, 115, 22, 0.25)",
    ))
    fig.update_layout(polar=dict(
        radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%", tickfont=dict(color="#374151")),
        angularaxis=dict(tickfont=dict(color="#111827", size=12)),
    ))
    apply_common_layout(fig, title=f"{player_a} vs {player_b} ({selected_year})", height=550)
    st.plotly_chart(fig, use_container_width=True, theme=None)
else:
    st.info("두 선수 중 레이더 차트를 그릴 데이터가 부족한 선수가 있습니다.")

st.divider()
st.subheader("📋 기본 성적 비교")

compare_cols_batter = ["hit_AVG", "hit_HR", "hit_RBI", "hit_OBP", "hit_SLG", "hit_OPS"]
compare_cols_pitcher = ["pit_ERA", "pit_WHIP", "pit_W", "pit_L", "pit_SV", "pit_SO", "pit_BB"]


def korean_label(col):
    return STAT_GLOSSARY[col][0] if col in STAT_GLOSSARY else col


col_left, col_right = st.columns(2)
with col_left:
    st.markdown(f"**{player_a}**")
    cols = compare_cols_pitcher if is_pitcher_a else compare_cols_batter
    if row_a is not None:
        table = row_a[cols].to_frame(name=player_a)
        table.index = [korean_label(c) for c in table.index]
        st.dataframe(table, use_container_width=True)
with col_right:
    st.markdown(f"**{player_b}**")
    cols = compare_cols_pitcher if is_pitcher_b else compare_cols_batter
    if row_b is not None:
        table = row_b[cols].to_frame(name=player_b)
        table.index = [korean_label(c) for c in table.index]
        st.dataframe(table, use_container_width=True)
