"""
pages/6_승률시뮬레이터.py
---------------------------
피타고리안 승률(Pythagorean Win Expectancy) 시뮬레이터.
WinPct = RS² / (RS² + RA²)
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from utils.data_loader import load_data, get_years, get_teams
from utils.style import apply_common_layout, COLOR_SEQUENCE

st.set_page_config(page_title="피타고리안 승률 시뮬레이터", page_icon="🎯", layout="wide")

df = load_data()
years = get_years(df)

st.title("🎯 피타고리안 승률 시뮬레이터")
st.caption(
    "빌 제임스의 피타고리안 기대승률 공식: **WinPct = 득점² / (득점² + 실점²)**. "
    "실제 승률과 다르면, 그 팀이 '운이 좋았는지/나빴는지' 가늠하는 지표로 흔히 쓰입니다."
)

col_a, col_b = st.columns(2)
with col_a:
    selected_year = st.selectbox("시즌 선택", options=years, index=len(years) - 1)

season_df = df[df["year"] == selected_year].copy()
teams = get_teams(season_df)

with col_b:
    selected_team = st.selectbox("구단 선택", options=teams)

team_df = season_df[season_df["team"] == selected_team]
batters_team = team_df.dropna(subset=["hit_R"])
pitchers_team = team_df[team_df["primary_position"] == "투수"].dropna(subset=["pit_R", "pit_W", "pit_L"])

rs = batters_team["hit_R"].sum()
ra = pitchers_team["pit_R"].sum()
wins = pitchers_team["pit_W"].sum()
losses = pitchers_team["pit_L"].sum()

if rs == 0 or ra == 0 or (wins + losses) == 0:
    st.warning("이 팀/시즌은 득점·실점·승패 데이터가 부족해 계산할 수 없습니다.")
    st.stop()

actual_wpct = wins / (wins + losses) * 100
pyth_wpct = rs ** 2 / (rs ** 2 + ra ** 2) * 100
gap = actual_wpct - pyth_wpct

st.divider()
st.subheader(f"📌 {selected_team} {selected_year} 실제 기록")
m1, m2, m3, m4 = st.columns(4)
m1.metric("팀 득점(RS)", f"{int(rs):,}점")
m2.metric("팀 실점(RA)", f"{int(ra):,}점")
m3.metric("실제 승률", f"{actual_wpct:.1f}%", help=f"{int(wins)}승 {int(losses)}패")
m4.metric("피타고리안 기대승률", f"{pyth_wpct:.1f}%", delta=f"{gap:+.1f}%p (실제-기대)")

if gap > 3:
    st.info(f"🍀 실제 승률이 기대승률보다 {gap:.1f}%p 높습니다 — 접전 상황에서 강했거나 '운'이 따랐을 가능성이 있습니다.")
elif gap < -3:
    st.info(f"😥 실제 승률이 기대승률보다 {abs(gap):.1f}%p 낮습니다 — 득실점 차만큼 승수를 못 챙긴 시즌일 수 있습니다.")
else:
    st.info("실제 승률과 피타고리안 기대승률이 비슷합니다 — 득실점만큼 정직하게 승수를 챙긴 시즌입니다.")

st.divider()
st.subheader("🎛️ 시뮬레이터: 득점·실점이 달라지면?")

sim_col1, sim_col2 = st.columns(2)
with sim_col1:
    rs_change = st.slider("득점 증감(%)", min_value=-30, max_value=30, value=0, step=1)
with sim_col2:
    ra_change = st.slider("실점 증감(%)", min_value=-30, max_value=30, value=0, step=1)

sim_rs = rs * (1 + rs_change / 100)
sim_ra = ra * (1 + ra_change / 100)
sim_pyth_wpct = sim_rs ** 2 / (sim_rs ** 2 + sim_ra ** 2) * 100

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta", value=sim_pyth_wpct,
    number={"suffix": "%", "font": {"size": 40}},
    delta={"reference": actual_wpct, "relative": False, "valueformat": ".1f", "suffix": "%p"},
    title={"text": f"예상 승률 (실제 승률 {actual_wpct:.1f}% 대비)"},
    gauge={
        "axis": {"range": [0, 100], "tickcolor": "#111827"},
        "bar": {"color": COLOR_SEQUENCE[1]},
        "steps": [
            {"range": [0, 40], "color": "#FEE2E2"},
            {"range": [40, 60], "color": "#FEF3C7"},
            {"range": [60, 100], "color": "#DCFCE7"},
        ],
        "threshold": {"line": {"color": "#111827", "width": 3}, "thickness": 0.8, "value": actual_wpct},
    },
))
apply_common_layout(fig_gauge, height=380)
st.plotly_chart(fig_gauge, use_container_width=True, theme=None)
st.caption(f"조정 시나리오: 득점 {rs:.0f}→{sim_rs:.0f}점, 실점 {ra:.0f}→{sim_ra:.0f}점.")

st.divider()
st.subheader("🍀 전체 구단 '승운' 리더보드 (실제승률 − 기대승률)")

rows = []
for t in teams:
    t_df = season_df[season_df["team"] == t]
    t_rs = t_df.dropna(subset=["hit_R"])["hit_R"].sum()
    t_pitchers = t_df[t_df["primary_position"] == "투수"].dropna(subset=["pit_R", "pit_W", "pit_L"])
    t_ra = t_pitchers["pit_R"].sum()
    t_w, t_l = t_pitchers["pit_W"].sum(), t_pitchers["pit_L"].sum()
    if t_rs > 0 and t_ra > 0 and (t_w + t_l) > 0:
        t_actual = t_w / (t_w + t_l) * 100
        t_pyth = t_rs ** 2 / (t_rs ** 2 + t_ra ** 2) * 100
        rows.append({"team": t, "gap": t_actual - t_pyth})

luck_df = pd.DataFrame(rows).sort_values("gap")
if not luck_df.empty:
    colors = ["#EF4444" if v < 0 else "#10B981" for v in luck_df["gap"]]
    fig_luck = go.Figure(go.Bar(
        x=luck_df["gap"], y=luck_df["team"], orientation="h", marker_color=colors,
        text=[f"{v:+.1f}%p" for v in luck_df["gap"]], textposition="outside",
    ))
    fig_luck.add_vline(x=0, line_color="#94A3B8")
    fig_luck.update_xaxes(title="실제승률 − 기대승률 (%p)")
    apply_common_layout(fig_luck, height=420)
    st.plotly_chart(fig_luck, use_container_width=True, theme=None)
