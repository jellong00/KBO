"""
pages/3_선수검색.py
---------------------
선수 선택(구단 -> 포지션 -> 선수, 검색란 병행)
-> 커리어 핵심 요약(KPI 카드) -> 핵심 지표 큰 추이 차트 2개(+선택 추가지표)
-> 커리어 프로파일 차트(커리어 내 백분위, 여러 지표 한 화면)
-> (참고) 포지션 대비 백분위 레이더
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

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
# 커리어 핵심 요약 (KPI 카드)
# ---------------------------------------------------------------
st.subheader("🏆 커리어 핵심 요약")

n_seasons = player_df["year"].nunique()

if is_pitcher:
    best_era_row = player_df.dropna(subset=["pit_ERA"]).loc[player_df["pit_ERA"].idxmin()] \
        if player_df["pit_ERA"].notna().any() else None
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("통산 시즌 수", f"{n_seasons}시즌")
    k2.metric("최고(최저) ERA", f"{player_df['pit_ERA'].min():.2f}" if player_df["pit_ERA"].notna().any() else "N/A")
    k3.metric("최다 탈삼진(단일시즌)", f"{int(player_df['pit_SO'].max()):,}" if player_df["pit_SO"].notna().any() else "N/A")
    k4.metric("최다 승수(단일시즌)", f"{int(player_df['pit_W'].max()):,}" if player_df["pit_W"].notna().any() else "N/A")
    k5.metric("최고 시즌(ERA 기준)", f"{int(best_era_row['year'])}년" if best_era_row is not None else "N/A")
else:
    best_ops_row = player_df.dropna(subset=["hit_OPS"]).loc[player_df["hit_OPS"].idxmax()] \
        if player_df["hit_OPS"].notna().any() else None
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("통산 시즌 수", f"{n_seasons}시즌")
    k2.metric("최고 OPS(단일시즌)", f"{player_df['hit_OPS'].max():.3f}" if player_df["hit_OPS"].notna().any() else "N/A")
    k3.metric("최고 AVG(단일시즌)", f"{player_df['hit_AVG'].max():.3f}" if player_df["hit_AVG"].notna().any() else "N/A")
    k4.metric("최다 HR(단일시즌)", f"{int(player_df['hit_HR'].max()):,}" if player_df["hit_HR"].notna().any() else "N/A")
    k5.metric("최고 시즌(OPS 기준)", f"{int(best_ops_row['year'])}년" if best_ops_row is not None else "N/A")

st.divider()

# ---------------------------------------------------------------
# 핵심 지표 추이 (큰 차트 2개)
# ---------------------------------------------------------------
st.subheader("📈 핵심 지표 추이")

if is_pitcher:
    primary_metrics = [("ERA (평균자책점)", "pit_ERA"), ("탈삼진(SO)", "pit_SO")]
    extra_options = {"WHIP": "pit_WHIP", "이닝(IP)": "pit_IP", "승수(W)": "pit_W"}
else:
    primary_metrics = [("OPS", "hit_OPS"), ("홈런(HR)", "hit_HR")]
    extra_options = {"타율(AVG)": "hit_AVG", "출루율(OBP)": "hit_OBP", "타점(RBI)": "hit_RBI"}

render_glossary([c for _, c in primary_metrics] + list(extra_options.values()) + ["pit_K9", "pit_BB9", "pit_HR9"])

for label, col in primary_metrics:
    fig_big = go.Figure()
    fig_big.add_trace(go.Scatter(
        x=player_df["year"], y=player_df[col], mode="lines+markers",
        line=dict(width=3, color=COLOR_SEQUENCE[0]), marker=dict(size=9),
    ))
    fig_big.update_xaxes(title="시즌", dtick=1)
    fig_big.update_yaxes(title=label)
    apply_common_layout(fig_big, title=f"{selected_player} — {label} 추이", height=340)
    st.plotly_chart(fig_big, use_container_width=True, theme=None)

selected_extra = st.multiselect("추가로 볼 지표 선택 (선택)", options=list(extra_options.keys()))
for label in selected_extra:
    col = extra_options[label]
    fig_extra = go.Figure()
    fig_extra.add_trace(go.Scatter(
        x=player_df["year"], y=player_df[col], mode="lines+markers",
        line=dict(width=2, color=COLOR_SEQUENCE[2]), marker=dict(size=7),
    ))
    fig_extra.update_xaxes(title="시즌", dtick=1)
    fig_extra.update_yaxes(title=label)
    apply_common_layout(fig_extra, title=f"{selected_player} — {label} 추이", height=280)
    st.plotly_chart(fig_extra, use_container_width=True, theme=None)

st.divider()

# ---------------------------------------------------------------
# 커리어 프로파일 차트 (커리어 내 백분위, 여러 지표 한 화면)
# ---------------------------------------------------------------
st.subheader("🧭 커리어 프로파일 차트")
st.caption("각 시즌의 값을 '이 선수 본인의 커리어 안에서'의 백분위(0~100)로 환산해, 여러 지표를 같은 스케일에서 비교합니다. 100에 가까울수록 그 선수 커리어 내 최고 수준의 시즌입니다.")


def career_percentile(series, higher_is_better=True):
    pct = series.rank(pct=True) * 100
    if not higher_is_better:
        pct = 100 - pct
    return pct


if is_pitcher:
    profile_axes = [("ERA↓", "pit_ERA", False), ("WHIP↓", "pit_WHIP", False), ("탈삼진(SO)", "pit_SO", True)]
else:
    profile_axes = [("타율(AVG)", "hit_AVG", True), ("OPS", "hit_OPS", True), ("홈런(HR)", "hit_HR", True)]

fig_profile = go.Figure()
for i, (label, col, higher_better) in enumerate(profile_axes):
    sub = player_df.dropna(subset=[col])
    if sub.empty or sub[col].nunique() < 2:
        continue
    pct_series = career_percentile(sub[col], higher_is_better=higher_better)
    fig_profile.add_trace(go.Scatter(
        x=sub["year"], y=pct_series, mode="lines+markers", name=label,
        line=dict(width=3, color=COLOR_SEQUENCE[i % len(COLOR_SEQUENCE)]), marker=dict(size=8),
    ))
fig_profile.update_xaxes(title="시즌", dtick=1)
fig_profile.update_yaxes(title="커리어 내 백분위", range=[-5, 105])
apply_common_layout(fig_profile, title=f"{selected_player} 커리어 프로파일", height=440)
st.plotly_chart(fig_profile, use_container_width=True, theme=None)

st.divider()

# ---------------------------------------------------------------
# (참고) 포지션 대비 백분위 레이더
# ---------------------------------------------------------------
with st.expander("🕸️ (참고) 포지션 대비 백분위 레이더 — 같은 시즌 동료 선수들과 비교"):
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
            "탈삼진율(K9)": ("pit_K9", True), "제구력(BB9↓)": ("pit_BB9", False),
            "피홈런 억제(HR9↓)": ("pit_HR9", False), "ERA↓": ("pit_ERA", False), "WHIP↓": ("pit_WHIP", False),
        }
    else:
        radar_axes = {
            "타율": ("hit_AVG", True), "출루율": ("hit_OBP", True), "장타율": ("hit_SLG", True),
            "홈런": ("hit_HR", True), "OPS": ("hit_OPS", True),
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
            line=dict(color=COLOR_SEQUENCE[0], width=2), fillcolor="rgba(37, 99, 235, 0.25)",
        ))
        radar_fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%", tickfont=dict(color="#374151")),
                angularaxis=dict(tickfont=dict(color="#111827", size=12)),
            ),
            showlegend=False,
        )
        apply_common_layout(radar_fig, title=f"{selected_player} 포지션 대비 백분위 ({int(latest_season)})", height=460)
        st.plotly_chart(radar_fig, use_container_width=True, theme=None)
    else:
        st.info("레이더 차트를 계산할 지표가 부족합니다.")

with st.expander("📋 원본 시즌별 기록 보기"):
    st.dataframe(player_df, use_container_width=True, hide_index=True)
