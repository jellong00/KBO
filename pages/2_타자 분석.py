"""
pages/2_Batter_Rank.py
------------------------
타자 분석: 규정타석 필터, 정렬 가능 테이블, 세이버메트릭스 버블차트,
주루 4분면 분석, 포지션별 수비율 분포(Violin)
"""

import pandas as pd
import streamlit as st
import plotly.express as px

from utils.data_loader import load_data, get_years
from utils.style import apply_common_layout, COLOR_SEQUENCE

st.set_page_config(page_title="타자 분석", page_icon="🏏", layout="wide")

df = load_data()
years = get_years(df)

st.title("🏏 타자 분석")

# ---------------------------------------------------------------
# 필터
# ---------------------------------------------------------------
col_a, col_b = st.columns([1, 2])
with col_a:
    selected_year = st.selectbox("시즌 선택", options=years, index=len(years) - 1)

season_df = df[df["year"] == selected_year].copy()
max_pa = int(season_df["hit_PA"].max()) if season_df["hit_PA"].notna().any() else 0

with col_b:
    pa_range = st.slider(
        "규정 타석(hit_PA) 필터",
        min_value=0,
        max_value=max_pa if max_pa > 0 else 1,
        value=(int(max_pa * 0.5), max_pa) if max_pa > 0 else (0, 1),
    )

batters = season_df[
    (season_df["hit_PA"] >= pa_range[0]) & (season_df["hit_PA"] <= pa_range[1])
].copy()
batters = batters.dropna(subset=["hit_AVG"])

st.caption(f"조건을 만족하는 타자: {batters['player_name'].nunique()}명")

st.divider()

# ---------------------------------------------------------------
# 정렬 가능한 데이터프레임
# ---------------------------------------------------------------
st.subheader("📋 타자 기록 테이블")

display_cols = [
    "player_name", "team", "def_POS", "hit_PA", "hit_AB", "hit_H",
    "hit_2B", "hit_3B", "hit_HR", "hit_RBI", "hit_AVG",
    "hit_OBP_est", "hit_SLG", "hit_OPS_est", "hit_wOBA_est",
]
display_cols = [c for c in display_cols if c in batters.columns]

st.dataframe(
    batters[display_cols].sort_values("hit_AVG", ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={
        "hit_AVG": st.column_config.NumberColumn("타율", format="%.3f"),
        "hit_OBP_est": st.column_config.NumberColumn("출루율(추정)", format="%.3f"),
        "hit_SLG": st.column_config.NumberColumn("장타율", format="%.3f"),
        "hit_OPS_est": st.column_config.NumberColumn("OPS(추정)", format="%.3f"),
        "hit_wOBA_est": st.column_config.NumberColumn("wOBA(추정)", format="%.3f"),
    },
)
st.caption(
    "⚠️ 이 데이터셋에는 타자 볼넷(BB)·사구(HBP) 컬럼이 없어, "
    "PA - AB - SF - SAC 로 역산한 근사치를 사용해 출루율/OPS/wOBA를 추정했습니다. "
    "실제 공식 기록과 다소 차이가 날 수 있습니다."
)

st.divider()

# ---------------------------------------------------------------
# 세이버메트릭스 버블 차트 (OPS/wOBA 추정치, 버블크기 = 타석수)
# ---------------------------------------------------------------
st.subheader("💠 세이버메트릭스 버블 차트 (wOBA vs OPS, 크기=타석수)")

bubble_df = batters.dropna(subset=["hit_wOBA_est", "hit_OPS_est"])
if not bubble_df.empty:
    fig_bubble = px.scatter(
        bubble_df,
        x="hit_wOBA_est",
        y="hit_OPS_est",
        size="hit_PA",
        color="team",
        hover_name="player_name",
        hover_data={"hit_HR": True, "hit_AVG": ":.3f", "hit_PA": True},
        labels={"hit_wOBA_est": "wOBA(추정)", "hit_OPS_est": "OPS(추정)", "team": "구단"},
        size_max=45,
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    apply_common_layout(fig_bubble, height=500)
    st.plotly_chart(fig_bubble, use_container_width=True)
else:
    st.info("표시할 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# 주루 4분면 분석 (도루 시도 vs 성공률, 색상=주루사)
# ---------------------------------------------------------------
st.subheader("🏃 주루 4분면 분석 (도루시도 vs 성공률)")

run_df = season_df.dropna(subset=["run_SBA", "run_SB_pct"])
run_df = run_df[run_df["run_SBA"] > 0]

if not run_df.empty:
    sba_mid = run_df["run_SBA"].median()
    pct_mid = run_df["run_SB_pct"].median()

    fig_quad = px.scatter(
        run_df,
        x="run_SBA",
        y="run_SB_pct",
        color="run_OOB",
        color_continuous_scale="RdYlGn_r",
        size="run_SBA",
        size_max=30,
        hover_name="player_name",
        hover_data={"team": True, "run_SB": True, "run_CS": True, "run_OOB": True},
        labels={"run_SBA": "도루 시도", "run_SB_pct": "도루 성공률(%)", "run_OOB": "주루사"},
    )
    fig_quad.add_vline(x=sba_mid, line_dash="dash", line_color="#94A3B8")
    fig_quad.add_hline(y=pct_mid, line_dash="dash", line_color="#94A3B8")
    apply_common_layout(fig_quad, height=520)
    st.plotly_chart(fig_quad, use_container_width=True)
    st.caption("점선은 중앙값 기준선이며, 4개 사분면으로 '고빈도-고성공', '고빈도-저성공' 등 유형을 구분할 수 있습니다. 색상이 진할수록 주루사(run_OOB)가 많음을 의미합니다.")
else:
    st.info("도루 시도 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# 포지션별 수비율 분포 (Violin Plot)
# ---------------------------------------------------------------
st.subheader("🧤 포지션별 수비율(FPCT) 분포")

def_df = season_df.dropna(subset=["def_FPCT", "def_POS"])
def_df = def_df[(def_df["def_POS"] != "") & (def_df["def_POS"] != "투수")]

if not def_df.empty:
    fig_violin = px.violin(
        def_df,
        x="def_POS",
        y="def_FPCT",
        color="def_POS",
        box=True,
        points="outliers",
        labels={"def_POS": "포지션", "def_FPCT": "수비율"},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig_violin.update_layout(showlegend=False)
    apply_common_layout(fig_violin, height=500)
    st.plotly_chart(fig_violin, use_container_width=True)
else:
    st.info("수비율 데이터가 부족합니다.")
