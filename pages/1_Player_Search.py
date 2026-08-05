"""
pages/1_Player_Search.py
-------------------------
선수명 검색 -> 통산 성적 추이(Line) + 포지션 대비 백분위 레이더 차트(Radar)
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from utils.data_loader import load_data
from utils.style import apply_common_layout, COLOR_SEQUENCE

st.set_page_config(page_title="선수 상세 분석", page_icon="🔍", layout="wide")

df = load_data()

st.title("🔍 선수 상세 분석")

# ---------------------------------------------------------------
# 선수 검색 및 선택
# ---------------------------------------------------------------
all_players = sorted(df["player_name"].dropna().unique().tolist())
search_term = st.text_input("선수명 검색", placeholder="예: 이정후, 김광현 ...")

filtered_names = [p for p in all_players if search_term.strip() in p] if search_term else all_players

if not filtered_names:
    st.warning("검색 결과가 없습니다.")
    st.stop()

selected_player = st.selectbox("선수 선택", options=filtered_names)

player_df = df[df["player_name"] == selected_player].sort_values("year")

if player_df.empty:
    st.info("해당 선수의 기록이 없습니다.")
    st.stop()

# 주 포지션 판정: 가장 많이 출전한 포지션
primary_pos = player_df["def_POS"].mode()
primary_pos = primary_pos.iloc[0] if not primary_pos.empty else ""
is_pitcher = primary_pos == "투수"

st.caption(f"주 포지션: **{primary_pos or '미상'}** · 기록 시즌: {player_df['year'].min()}~{player_df['year'].max()}")

st.divider()

# ---------------------------------------------------------------
# Chart 1: 통산 시즌별 주요 성적 추이 (Line Chart)
# ---------------------------------------------------------------
st.subheader("📈 통산 시즌별 성적 추이")

if is_pitcher:
    metric_options = {
        "ERA (평균자책점)": "pit_ERA",
        "WHIP": "pit_WHIP",
        "탈삼진(SO)": "pit_SO",
        "이닝(IP)": "pit_IP",
        "승수(W)": "pit_W",
    }
else:
    metric_options = {
        "타율(AVG)": "hit_AVG",
        "홈런(HR)": "hit_HR",
        "OPS(추정)": "hit_OPS_est",
        "타점(RBI)": "hit_RBI",
        "출루율(추정)": "hit_OBP_est",
    }

selected_metrics = st.multiselect(
    "표시할 지표 선택",
    options=list(metric_options.keys()),
    default=list(metric_options.keys())[:2],
)

if selected_metrics:
    fig = go.Figure()
    for i, m_label in enumerate(selected_metrics):
        col = metric_options[m_label]
        if col not in player_df.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=player_df["year"],
                y=player_df[col],
                mode="lines+markers",
                name=m_label,
                line=dict(width=3, color=COLOR_SEQUENCE[i % len(COLOR_SEQUENCE)]),
                marker=dict(size=8),
            )
        )
    apply_common_layout(fig, title=f"{selected_player} 시즌별 추이", height=460)
    fig.update_xaxes(title="시즌", dtick=1)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("표시할 지표를 1개 이상 선택하세요.")

st.divider()

# ---------------------------------------------------------------
# Chart 2: 포지션 대비 주요 능력치 백분위 레이더 차트
# ---------------------------------------------------------------
st.subheader("🕸️ 포지션 대비 백분위 레이더 차트")

latest_season = player_df["year"].max()
latest_row = player_df[player_df["year"] == latest_season].iloc[0]

cohort = df[(df["def_POS"] == primary_pos) & (df["year"] == latest_season)]

st.caption(f"비교 기준: {latest_season} 시즌 · 포지션 '{primary_pos}' 동료 {cohort['player_name'].nunique()}명 대비 백분위")


def percentile_of(series, value, higher_is_better=True):
    """cohort 내에서 value의 백분위(0~100)를 계산. 결측 처리 포함."""
    s = series.dropna()
    if s.empty or pd.isna(value):
        return 0
    pct = (s < value).sum() / len(s) * 100 if higher_is_better else (s > value).sum() / len(s) * 100
    return round(pct, 1)


if is_pitcher:
    radar_axes = {
        "탈삼진율(K9)": ("pit_K9", True),
        "제구력(BB9↓)": ("pit_BB9", False),
        "피홈런 억제(HR9↓)": ("pit_HR9", False),
        "ERA↓": ("pit_ERA", False),
        "WHIP↓": ("pit_WHIP", False),
    }
else:
    radar_axes = {
        "타율": ("hit_AVG", True),
        "출루율(추정)": ("hit_OBP_est", True),
        "장타율": ("hit_SLG", True),
        "홈런": ("hit_HR", True),
        "wOBA(추정)": ("hit_wOBA_est", True),
    }

labels, values = [], []
for label, (col, higher_better) in radar_axes.items():
    if col not in df.columns:
        continue
    val = latest_row.get(col, np.nan)
    pct = percentile_of(cohort[col], val, higher_is_better=higher_better)
    labels.append(label)
    values.append(pct)

if labels:
    radar_fig = go.Figure()
    radar_fig.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name=selected_player,
            line=dict(color=COLOR_SEQUENCE[0], width=2),
            fillcolor="rgba(37, 99, 235, 0.25)",
        )
    )
    radar_fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%")),
        showlegend=False,
    )
    apply_common_layout(radar_fig, title=f"{selected_player} 포지션 대비 백분위 ({latest_season})", height=500)
    st.plotly_chart(radar_fig, use_container_width=True)
else:
    st.info("레이더 차트를 계산할 지표가 부족합니다.")

with st.expander("📋 원본 시즌별 기록 보기"):
    st.dataframe(player_df, use_container_width=True, hide_index=True)
