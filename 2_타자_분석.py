from __future__ import annotations

import plotly.express as px
import streamlit as st

from utils.data import batting_data, filter_data, load_data
from utils.ui import PLOTLY_CONFIG, global_filters, modernize, setup_page

setup_page("KBO 타자 분석")
df = load_data()

st.title("타자 분석")
years, teams = global_filters(df, "bat")
min_pa = st.sidebar.number_input("최소 타석", min_value=0, max_value=700, value=100, step=10)
bat = batting_data(filter_data(df, years, teams), min_pa=int(min_pa))

if bat.empty:
    st.warning("선택 조건을 만족하는 타자 기록이 없습니다.")
    st.stop()

metric_options = {
    "hit_OPS": "OPS",
    "hit_OBP": "출루율",
    "hit_SLG": "장타율",
    "hit_AVG": "타율",
    "hit_HR": "홈런",
    "hit_RBI": "타점",
    "hit_wOBA_simple": "간이 wOBA",
}
metric = st.selectbox("순위 지표", list(metric_options), format_func=metric_options.get)
top_n = st.slider("상위 선수 수", 5, 40, 15)
ranking = bat.nlargest(top_n, metric)[["player_name", "year", "team", "hit_PA", metric]].copy()
ranking["선수-시즌"] = ranking["player_name"].astype(str) + " (" + ranking["year"].astype(str) + ", " + ranking["team"].astype(str) + ")"

fig = px.bar(ranking.sort_values(metric), x=metric, y="선수-시즌", orientation="h", text=metric)
modernize(fig, f"{metric_options[metric]} 상위 {top_n}명", height=max(480, top_n * 28))
fig.update_traces(texttemplate="%{text:.3f}" if metric in {"hit_OPS", "hit_OBP", "hit_SLG", "hit_AVG", "hit_wOBA_simple"} else "%{text:.0f}")
st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

st.subheader("출루 능력과 장타 능력")
size_metric = st.selectbox("점 크기", ["hit_PA", "hit_HR", "hit_RBI"], format_func={"hit_PA": "타석", "hit_HR": "홈런", "hit_RBI": "타점"}.get)
fig = px.scatter(
    bat,
    x="hit_OBP",
    y="hit_SLG",
    size=size_metric,
    color="year",
    hover_name="player_name",
    hover_data={"team": True, "year": True, "hit_OPS": ":.3f", "hit_PA": ":.0f"},
    render_mode="webgl",
)
modernize(fig, "출루율-장타율 분포", height=600)
fig.update_xaxes(tickformat=".3f")
fig.update_yaxes(tickformat=".3f")
st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

st.subheader("연도별 홈런 분포")
fig = px.box(bat, x="year", y="hit_HR", points=False)
modernize(fig, "최소 타석 기준 선수별 홈런 분포")
st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

with st.expander("필터링된 데이터 보기"):
    cols = ["player_name", "year", "team", "hit_PA", "hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS", "hit_HR", "hit_RBI"]
    st.dataframe(bat[cols].sort_values(["year", "hit_OPS"], ascending=[False, False]), use_container_width=True, hide_index=True)
