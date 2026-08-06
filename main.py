from __future__ import annotations

import plotly.express as px
import streamlit as st

from utils.data import batting_data, load_data, pitching_data
from utils.ui import PLOTLY_CONFIG, modernize, setup_page

setup_page("KBO 기록 분석 대시보드")

df = load_data()
bat = batting_data(df)
pit = pitching_data(df)

st.title("⚾ KBO 기록 분석 대시보드")
st.caption("2001–2025 선수-시즌 데이터를 탐색하고, 타격·투구 성과와 확률 시뮬레이션을 분석합니다.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("선수-시즌", f"{len(df):,}")
c2.metric("고유 선수", f"{df['player_id'].nunique():,}")
c3.metric("분석 기간", f"{int(df['year'].min())}–{int(df['year'].max())}")
c4.metric("구단명", f"{df['team'].nunique():,}")

st.subheader("리그 장기 추세")
left, right = st.columns(2)

with left:
    yearly_bat = (
        bat[bat["hit_PA"].fillna(0) >= 100]
        .groupby("year", as_index=False)
        .agg(OPS=("hit_OPS", "mean"), HR=("hit_HR", "sum"), PA=("hit_PA", "sum"))
    )
    fig = px.line(yearly_bat, x="year", y="OPS", markers=True)
    modernize(fig, "연도별 평균 OPS (100타석 이상 선수)")
    fig.update_yaxes(tickformat=".3f")
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

with right:
    yearly_pit = (
        pit[pit["pit_IP_num"] >= 30]
        .groupby("year", as_index=False)
        .agg(ERA=("pit_ERA", "mean"), K9=("pit_K_9", "mean"))
    )
    fig = px.line(yearly_pit, x="year", y=["ERA", "K9"], markers=True)
    modernize(fig, "연도별 평균 ERA와 K/9 (30이닝 이상)")
    fig.update_layout(yaxis_title="평균값", legend_title_text="지표")
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

st.subheader("페이지 안내")
st.markdown(
    """
- **리그 개요**: 연도·구단별 공격력과 투수력 비교
- **타자 분석**: OPS, 장타율, 출루율, 홈런 등 타격 지표 탐색
- **투수 분석**: ERA, WHIP, K/9, BB/9 및 승패 성과 비교
- **선수 탐색**: 특정 선수의 시즌별 기록과 커리어 변화 확인
- **확률 시뮬레이터**: 선택한 타자의 과거 이벤트 비율로 가상 시즌을 반복 생성

왼쪽 사이드바에서 각 페이지로 이동할 수 있습니다.
"""
)

st.info(
    "시뮬레이션은 교육용 확률 모형입니다. 상대 투수, 구장, 부상, 연령 변화 등은 반영하지 않으므로 미래 예측치로 해석하면 안 됩니다."
)
