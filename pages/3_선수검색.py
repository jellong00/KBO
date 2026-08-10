"""
pages/2_선수검색.py
---------------------
선수 선택(구단 -> 포지션 -> 선수, 검색란 병행) -> 통산 성적 추이(소multiples)
+ 포지션 대비 백분위 레이더 차트
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.data_loader import load_data, get_teams, get_positions
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import render_glossary

st.set_page_config(page_title="선수 검색", page_icon="🔍", layout="wide")

df = load_data()

st.title("🔍 선수 검색 · 개인 커리어")

st.subheader("선수 선택")
search_term = st.text_input("🔎 이름으로 빠르게 찾기 (선택)", placeholder="예: 이정후, 김광현 ...")

col_team, col_pos, col_player = st.columns([1, 1, 1.4])

with col_team:
    team_sel = st.selectbox("① 구단 선택", options=["전체"] + get_teams(df))

pool = df if team_sel == "전체" else df[df["team"] == team_sel]

with col_pos:
    position_options = ["전체"] + get_positions(pool)
    pos_sel = st.selectbox("② 포지션 선택", options=position_options)

if pos_sel != "전체":
    # positions_played는 ", "로 겸한 포지션이 나열되어 있으므로 포함 여부로 필터링
    pool = pool[pool["positions_played"].str.contains(pos_sel, na=False)]

candidate_names = sorted(pool["player_name"].dropna().unique().tolist())
if search_term:
    candidate_names = [p for p in candidate_names if search_term.strip() in p]

with col_player:
    if not candidate_names:
        st.selectbox("③ 선수 선택", options=["(해당 없음)"], disabled=True)
        st.warning("조건에 맞는 선수가 없습니다. 구단/포지션/검색어를 다시 확인해주세요.")
        st.stop()
    selected_player = st.selectbox("③ 선수 선택", options=candidate_names)

# 이후 분석은 선수의 전체 통산 기록 기준
player_df = df[df["player_name"] == selected_player].sort_values("year")

if player_df.empty:
    st.info("해당 선수의 기록이 없습니다.")
    st.stop()

if pos_sel != "전체":
    primary_pos = pos_sel
else:
    primary_pos = player_df.iloc[-1]["primary_position"]
is_pitcher = primary_pos == "투수"

st.caption(f"주 포지션(기준): **{primary_pos or '미상'}** · 기록 시즌: {int(player_df['year'].min())}~{int(player_df['year'].max())}")

st.divider()

# ---------------------------------------------------------------
# Chart 1: 통산 시즌별 주요 성적 추이 (소multiples)
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
        "OPS": "hit_OPS",
        "타점(RBI)": "hit_RBI",
        "출루율(OBP)": "hit_OBP",
    }

render_glossary(list(metric_options.values()) + ["pit_K9", "pit_BB9", "pit_HR9"])

selected_metrics = st.multiselect(
    "표시할 지표 선택 (지표마다 스케일이 달라 각각 별도 축으로 표시됩니다)",
    options=list(metric_options.keys()),
    default=list(metric_options.keys())[:3],
)

if selected_metrics:
    n = len(selected_metrics)
    fig = make_subplots(
        rows=n, cols=1, shared_xaxes=True,
        subplot_titles=selected_metrics,
        vertical_spacing=min(0.12, 0.6 / n),
    )
    for i, m_label in enumerate(selected_metrics):
        col = metric_options[m_label]
        if col not in player_df.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=player_df["year"], y=player_df[col],
                mode="lines+markers", name=m_label,
                line=dict(width=3, color=COLOR_SEQUENCE[i % len(COLOR_SEQUENCE)]),
                marker=dict(size=8), showlegend=False,
            ),
            row=i + 1, col=1,
        )
        fig.update_yaxes(title_text=m_label, row=i + 1, col=1)

    fig.update_xaxes(title="시즌", dtick=1, row=n, col=1)
    apply_common_layout(fig, title=f"{selected_player} 시즌별 추이", height=230 * n)
    fig.update_annotations(font=dict(color="#111827", size=13))
    st.plotly_chart(fig, use_container_width=True, theme=None)
else:
    st.info("표시할 지표를 1개 이상 선택하세요.")

st.divider()

# ---------------------------------------------------------------
# Chart 2: 포지션 대비 주요 능력치 백분위 레이더 차트
# ---------------------------------------------------------------
st.subheader("🕸️ 포지션 대비 백분위 레이더 차트")

latest_season = player_df["year"].max()
latest_row = player_df[player_df["year"] == latest_season].iloc[0]

cohort = (
    df[(df["year"] == latest_season) & (df["positions_played"].str.contains(primary_pos, na=False))]
    if primary_pos else df[df["year"] == latest_season]
)

st.caption(f"비교 기준: {int(latest_season)} 시즌 · 포지션 '{primary_pos}' 동료 {cohort['player_name'].nunique()}명 대비 백분위")


def percentile_of(series, value, higher_is_better=True):
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
        "출루율": ("hit_OBP", True),
        "장타율": ("hit_SLG", True),
        "홈런": ("hit_HR", True),
        "OPS": ("hit_OPS", True),
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
    radar_fig.add_trace(go.Scatterpolar(
        r=values + [values[0]], theta=labels + [labels[0]],
        fill="toself", name=selected_player,
        line=dict(color=COLOR_SEQUENCE[0], width=2),
        fillcolor="rgba(37, 99, 235, 0.25)",
    ))
    radar_fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%", tickfont=dict(color="#374151")),
            angularaxis=dict(tickfont=dict(color="#111827", size=12)),
        ),
        showlegend=False,
    )
    apply_common_layout(radar_fig, title=f"{selected_player} 포지션 대비 백분위 ({int(latest_season)})", height=500)
    st.plotly_chart(radar_fig, use_container_width=True, theme=None)
else:
    st.info("레이더 차트를 계산할 지표가 부족합니다.")

with st.expander("📋 원본 시즌별 기록 보기"):
    st.dataframe(player_df, use_container_width=True, hide_index=True)
