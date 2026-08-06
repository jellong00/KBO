from __future__ import annotations

import plotly.express as px
import streamlit as st

from utils.data import batting_data, filter_data, load_data, pitching_data
from utils.ui import PLOTLY_CONFIG, global_filters, modernize, setup_page

setup_page("KBO 리그 개요")
df = load_data()

st.title("리그 개요")
years, teams = global_filters(df, "league")
filtered = filter_data(df, years, teams)

bat = batting_data(filtered, min_pa=1)
pit = pitching_data(filtered, min_ip=0.1)

c1, c2, c3, c4 = st.columns(4)
c1.metric("선수-시즌", f"{len(filtered):,}")
c2.metric("총 홈런", f"{bat['hit_HR'].fillna(0).sum():,.0f}")
c3.metric("총 득점", f"{bat['hit_R'].fillna(0).sum():,.0f}")
c4.metric("총 탈삼진", f"{pit['pit_SO'].fillna(0).sum():,.0f}")

team_bat = (
    bat.groupby(["year", "team"], as_index=False)
    .agg(PA=("hit_PA", "sum"), R=("hit_R", "sum"), HR=("hit_HR", "sum"), H=("hit_H", "sum"), BB=("hit_BB", "sum"))
)
team_bat["HR_600PA"] = team_bat["HR"] / team_bat["PA"].replace(0, float("nan")) * 600
team_bat["R_600PA"] = team_bat["R"] / team_bat["PA"].replace(0, float("nan")) * 600

team_pit = (
    pit.groupby(["year", "team"], as_index=False)
    .agg(IP=("pit_IP_num", "sum"), ER=("pit_ER", "sum"), H=("pit_H", "sum"), BB=("pit_BB", "sum"), SO=("pit_SO", "sum"))
)
team_pit["ERA_calc"] = team_pit["ER"] * 9 / team_pit["IP"].replace(0, float("nan"))
team_pit["WHIP_calc"] = (team_pit["H"] + team_pit["BB"]) / team_pit["IP"].replace(0, float("nan"))

left, right = st.columns(2)
with left:
    metric = st.selectbox("공격 지표", ["R_600PA", "HR_600PA"], format_func=lambda x: {"R_600PA": "600타석당 득점", "HR_600PA": "600타석당 홈런"}[x])
    fig = px.line(team_bat, x="year", y=metric, color="team", markers=True)
    modernize(fig, "구단별 공격 생산성")
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

with right:
    p_metric = st.selectbox("투구 지표", ["ERA_calc", "WHIP_calc"], format_func=lambda x: {"ERA_calc": "계산 ERA", "WHIP_calc": "계산 WHIP"}[x])
    fig = px.line(team_pit, x="year", y=p_metric, color="team", markers=True)
    modernize(fig, "구단별 투수 성과")
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

st.subheader("공격력-투수력 포지셔닝")
merged = team_bat.merge(team_pit, on=["year", "team"], suffixes=("_bat", "_pit"))
selected_year = st.select_slider("비교 연도", options=sorted(merged["year"].unique()), value=int(merged["year"].max()))
plot_df = merged[merged["year"] == selected_year]
fig = px.scatter(
    plot_df,
    x="ERA_calc",
    y="R_600PA",
    size="HR",
    color="team",
    text="team",
    hover_data={"WHIP_calc": ":.3f", "HR_600PA": ":.2f"},
)
modernize(fig, f"{selected_year}년 구단 포지셔닝", height=560)
fig.update_traces(textposition="top center")
fig.update_xaxes(title="ERA (낮을수록 우수)")
fig.update_yaxes(title="600타석당 득점 (높을수록 우수)")
st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
