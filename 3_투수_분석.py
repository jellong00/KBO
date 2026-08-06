from __future__ import annotations

import plotly.express as px
import streamlit as st

from utils.data import filter_data, load_data, pitching_data
from utils.ui import PLOTLY_CONFIG, global_filters, modernize, setup_page

setup_page("KBO 투수 분석")
df = load_data()

st.title("투수 분석")
years, teams = global_filters(df, "pit")
min_ip = st.sidebar.number_input("최소 이닝", min_value=0.0, max_value=250.0, value=30.0, step=10.0)
pit = pitching_data(filter_data(df, years, teams), min_ip=float(min_ip))

if pit.empty:
    st.warning("선택 조건을 만족하는 투수 기록이 없습니다.")
    st.stop()

metric_options = {
    "pit_ERA": "ERA (낮을수록 우수)",
    "pit_WHIP": "WHIP (낮을수록 우수)",
    "pit_K_9": "K/9",
    "pit_K_BB": "K/BB",
    "pit_SO": "탈삼진",
    "pit_W": "승리",
}
metric = st.selectbox("순위 지표", list(metric_options), format_func=metric_options.get)
ascending = metric in {"pit_ERA", "pit_WHIP"}
top_n = st.slider("상위 선수 수", 5, 40, 15)
rank_source = pit.dropna(subset=[metric])
ranking = rank_source.nsmallest(top_n, metric) if ascending else rank_source.nlargest(top_n, metric)
ranking = ranking[["player_name", "year", "team", "pit_IP_num", metric]].copy()
ranking["선수-시즌"] = ranking["player_name"].astype(str) + " (" + ranking["year"].astype(str) + ", " + ranking["team"].astype(str) + ")"

fig = px.bar(ranking.sort_values(metric, ascending=not ascending), x=metric, y="선수-시즌", orientation="h", text=metric)
modernize(fig, f"{metric_options[metric]} 상위 {top_n}명", height=max(480, top_n * 28))
fig.update_traces(texttemplate="%{text:.2f}")
st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

st.subheader("제구력과 탈삼진 능력")
fig = px.scatter(
    pit,
    x="pit_BB_9",
    y="pit_K_9",
    size="pit_IP_num",
    color="pit_ERA",
    hover_name="player_name",
    hover_data={"team": True, "year": True, "pit_WHIP": ":.2f", "pit_IP_num": ":.1f"},
    render_mode="webgl",
)
modernize(fig, "BB/9-K/9 분포", height=600)
fig.update_xaxes(title="BB/9 (낮을수록 우수)")
fig.update_yaxes(title="K/9 (높을수록 우수)")
st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

st.subheader("ERA와 수비 무관 지표의 관계")
fig = px.scatter(
    pit,
    x="pit_WHIP",
    y="pit_ERA",
    color="year",
    size="pit_IP_num",
    hover_name="player_name",
    hover_data=["team", "pit_K_9", "pit_BB_9"],
    trendline=None,
    render_mode="webgl",
)
modernize(fig, "WHIP-ERA 분포", height=560)
st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

with st.expander("필터링된 데이터 보기"):
    cols = ["player_name", "year", "team", "pit_IP_num", "pit_ERA", "pit_WHIP", "pit_K_9", "pit_BB_9", "pit_K_BB", "pit_W", "pit_L", "pit_SV"]
    st.dataframe(pit[cols].sort_values(["year", "pit_ERA"], ascending=[False, True]), use_container_width=True, hide_index=True)
