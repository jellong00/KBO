from __future__ import annotations

import plotly.express as px
import streamlit as st

from utils.data import load_data
from utils.ui import PLOTLY_CONFIG, modernize, setup_page

setup_page("KBO 선수 탐색")
df = load_data()

st.title("선수 탐색")
players = sorted(df["player_name"].dropna().astype(str).unique())
selected = st.selectbox("선수 선택", players, index=0)
player = df[df["player_name"] == selected].sort_values("year").copy()

st.subheader(f"{selected} 커리어 개요")
c1, c2, c3, c4 = st.columns(4)
c1.metric("활동 시즌", f"{player['year'].nunique()}시즌")
c2.metric("최초 기록", f"{int(player['year'].min())}")
c3.metric("최근 기록", f"{int(player['year'].max())}")
c4.metric("소속 구단 수", f"{player['team'].nunique()}")

batting_metrics = {
    "hit_OPS": "OPS",
    "hit_AVG": "타율",
    "hit_OBP": "출루율",
    "hit_SLG": "장타율",
    "hit_HR": "홈런",
    "hit_RBI": "타점",
}
pitching_metrics = {
    "pit_ERA": "ERA",
    "pit_WHIP": "WHIP",
    "pit_K_9": "K/9",
    "pit_BB_9": "BB/9",
    "pit_SO": "탈삼진",
    "pit_W": "승리",
}

left, right = st.columns(2)
with left:
    st.markdown("#### 타격 기록")
    b_metric = st.selectbox("타격 지표", list(batting_metrics), format_func=batting_metrics.get)
    bat = player[player["hit_PA"].fillna(0) > 0]
    if bat.empty or bat[b_metric].notna().sum() == 0:
        st.info("선택 선수의 해당 타격 기록이 없습니다.")
    else:
        fig = px.line(bat, x="year", y=b_metric, markers=True, hover_data=["team", "hit_PA"])
        modernize(fig, f"시즌별 {batting_metrics[b_metric]}")
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

with right:
    st.markdown("#### 투구 기록")
    p_metric = st.selectbox("투구 지표", list(pitching_metrics), format_func=pitching_metrics.get)
    pit = player[player["pit_IP_num"].fillna(0) > 0]
    if pit.empty or pit[p_metric].notna().sum() == 0:
        st.info("선택 선수의 해당 투구 기록이 없습니다.")
    else:
        fig = px.line(pit, x="year", y=p_metric, markers=True, hover_data=["team", "pit_IP_num"])
        modernize(fig, f"시즌별 {pitching_metrics[p_metric]}")
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

st.subheader("시즌 기록표")
show_cols = [
    "year", "team", "def_POS", "hit_G", "hit_PA", "hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS", "hit_HR", "hit_RBI",
    "pit_G", "pit_IP_num", "pit_ERA", "pit_WHIP", "pit_K_9", "pit_W", "pit_L", "pit_SV"
]
st.dataframe(player[[c for c in show_cols if c in player.columns]], use_container_width=True, hide_index=True)
