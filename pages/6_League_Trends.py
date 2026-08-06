"""
pages/6_League_Trends.py
--------------------------
심화 분석: 리그 전체의 시대적 흐름을 보여주는 재미있는 시각화 모음
 - 연도별 리그 타고/투고 흐름 (소multiples)
 - 연도별 구단 타율-홈런 변화 애니메이션 버블차트
 - 구단 x 연도 평균 ERA 히트맵
 - 역대(모든 시즌 통틀어) 한 시즌 최다 홈런 / 최저 ERA 리더보드
"""

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.data_loader import load_data, get_years
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import render_glossary

st.set_page_config(page_title="심화 분석 · 리그 트렌드", page_icon="📈", layout="wide")

df = load_data()
years = get_years(df)

st.title("📈 심화 분석: 리그 트렌드 & 역대 기록")
st.caption("개별 선수/구단이 아닌, KBO 리그 전체가 시간에 따라 어떻게 변해왔는지를 보여주는 페이지입니다.")
render_glossary(["hit_AVG", "hit_HR", "pit_ERA"])

# ---------------------------------------------------------------
# 1. 연도별 리그 타고/투고 흐름
# ---------------------------------------------------------------
st.subheader("1️⃣ 연도별 '타고투저' vs '투고타저' 흐름")

league_trend = (
    df.dropna(subset=["hit_AVG"]).groupby("year")["hit_AVG"].mean().rename("리그 평균 타율")
).to_frame()
league_trend["리그 평균 ERA"] = (
    df[df["def_POS"].str.contains("투수", na=False)].dropna(subset=["pit_ERA"]).groupby("year")["pit_ERA"].mean()
)
league_trend = league_trend.reset_index()

fig_trend = go.Figure()
fig_trend.add_trace(go.Scatter(
    x=league_trend["year"], y=league_trend["리그 평균 타율"],
    name="리그 평균 타율", mode="lines+markers",
    line=dict(color=COLOR_SEQUENCE[0], width=3), yaxis="y1",
))
fig_trend.add_trace(go.Scatter(
    x=league_trend["year"], y=league_trend["리그 평균 ERA"],
    name="리그 평균 ERA", mode="lines+markers",
    line=dict(color=COLOR_SEQUENCE[3], width=3, dash="dot"), yaxis="y2",
))
fig_trend.update_layout(
    yaxis=dict(title="리그 평균 타율"),
    yaxis2=dict(title="리그 평균 ERA", overlaying="y", side="right"),
    xaxis=dict(title="연도", dtick=2),
)
apply_common_layout(fig_trend, title="리그 평균 타율 vs 평균 ERA 추이", height=460)
st.plotly_chart(fig_trend, use_container_width=True)
st.caption(
    "타율 선이 올라가고 ERA 선도 함께 올라가는 구간은 '타고투저'(투수보다 타자가 유리한) 시기, "
    "반대로 둘 다 내려가는 구간은 '투고타저' 시기로 해석할 수 있습니다."
)

st.divider()

# ---------------------------------------------------------------
# 2. 연도별 구단 타율-홈런 변화 애니메이션 버블차트
# ---------------------------------------------------------------
st.subheader("2️⃣ 연도별 구단 타율-홈런 변화 (재생 버튼을 눌러보세요 ▶️)")

team_year = (
    df.dropna(subset=["hit_AVG"])
    .groupby(["year", "team"])
    .agg(팀평균타율=("hit_AVG", "mean"), 팀총홈런=("hit_HR", "sum"), 등록선수수=("player_name", "nunique"))
    .reset_index()
)

fig_anim = px.scatter(
    team_year,
    x="팀평균타율",
    y="팀총홈런",
    animation_frame="year",
    animation_group="team",
    color="team",
    size="등록선수수",
    hover_name="team",
    range_x=[team_year["팀평균타율"].min() * 0.95, team_year["팀평균타율"].max() * 1.05],
    range_y=[0, team_year["팀총홈런"].max() * 1.1],
    labels={"팀평균타율": "팀 평균 타율", "팀총홈런": "팀 총 홈런"},
    color_discrete_sequence=COLOR_SEQUENCE,
)
apply_common_layout(fig_anim, height=560)
st.plotly_chart(fig_anim, use_container_width=True)
st.caption("연도 슬라이더 또는 ▶️ 재생 버튼으로 구단들의 타격 스타일이 시즌마다 어떻게 이동하는지 확인할 수 있습니다.")

st.divider()

# ---------------------------------------------------------------
# 3. 구단 x 연도 평균 ERA 히트맵
# ---------------------------------------------------------------
st.subheader("3️⃣ 구단별 투수력 변화 히트맵 (평균 ERA)")

pitcher_df = df[df["def_POS"].str.contains("투수", na=False)].dropna(subset=["pit_ERA"])
heat = pitcher_df.groupby(["team", "year"])["pit_ERA"].mean().reset_index()
heat_pivot = heat.pivot(index="team", columns="year", values="pit_ERA")

fig_heat = px.imshow(
    heat_pivot,
    color_continuous_scale="RdYlGn_r",  # 낮은 ERA(좋음)=초록, 높은 ERA(나쁨)=빨강
    aspect="auto",
    labels=dict(x="연도", y="구단", color="평균 ERA"),
)
apply_common_layout(fig_heat, height=520)
fig_heat.update_xaxes(dtick=2)
st.plotly_chart(fig_heat, use_container_width=True)
st.caption("초록색일수록 그 해 평균자책점(ERA)이 낮아(우수) 투수력이 좋았던 시즌, 빨간색일수록 어려웠던 시즌입니다. 빈 칸은 해당 연도에 그 구단이 없었음(창단 전/해체/명칭변경)을 의미합니다.")

st.divider()

# ---------------------------------------------------------------
# 4. 역대 리더보드 (모든 시즌 통틀어)
# ---------------------------------------------------------------
st.subheader("4️⃣ 역대 한 시즌 최고 기록 리더보드")

lb1, lb2 = st.columns(2)

with lb1:
    st.markdown("**💣 역대 한 시즌 최다 홈런 Top 10**")
    hr_leaders = df.dropna(subset=["hit_HR"]).sort_values("hit_HR", ascending=False).head(10).copy()
    hr_leaders["표시"] = hr_leaders["player_name"] + " (" + hr_leaders["year"].astype(int).astype(str) + ")"
    fig_hr_lb = go.Figure(go.Bar(
        x=hr_leaders["hit_HR"][::-1],
        y=hr_leaders["표시"][::-1],
        orientation="h",
        marker_color=COLOR_SEQUENCE[3],
        text=hr_leaders["hit_HR"][::-1],
        textposition="outside",
    ))
    fig_hr_lb.update_xaxes(title="홈런")
    apply_common_layout(fig_hr_lb, height=430)
    st.plotly_chart(fig_hr_lb, use_container_width=True)

with lb2:
    st.markdown("**🎯 역대 한 시즌 최저 ERA Top 10 (규정이닝 100이닝 이상)**")
    era_leaders = df[df["pit_IP"] >= 100].dropna(subset=["pit_ERA"]).sort_values("pit_ERA", ascending=True).head(10).copy()
    era_leaders["표시"] = era_leaders["player_name"] + " (" + era_leaders["year"].astype(int).astype(str) + ")"
    fig_era_lb = go.Figure(go.Bar(
        x=era_leaders["pit_ERA"][::-1],
        y=era_leaders["표시"][::-1],
        orientation="h",
        marker_color=COLOR_SEQUENCE[2],
        text=era_leaders["pit_ERA"][::-1].round(2),
        textposition="outside",
    ))
    fig_era_lb.update_xaxes(title="ERA")
    apply_common_layout(fig_era_lb, height=430)
    st.plotly_chart(fig_era_lb, use_container_width=True)
