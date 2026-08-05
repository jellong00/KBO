"""
app.py
------
KBO 기록 분석 대시보드 - 메인 홈
실행: streamlit run app.py
"""

import streamlit as st
import plotly.express as px

from utils.data_loader import load_data, get_years
from utils.style import apply_common_layout, COLOR_SEQUENCE

st.set_page_config(
    page_title="KBO 기록 분석 대시보드",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------
# 데이터 로드
# ---------------------------------------------------------------
df = load_data()
years = get_years(df)

# ---------------------------------------------------------------
# 사이드바 - 시즌 필터
# ---------------------------------------------------------------
st.sidebar.title("⚾ KBO Dashboard")
st.sidebar.caption("메뉴에서 페이지를 선택하세요.")
st.sidebar.divider()

selected_year = st.sidebar.selectbox(
    "시즌(연도) 선택",
    options=years,
    index=len(years) - 1,
)

st.sidebar.divider()
qualified_only = st.sidebar.checkbox("규정 타석/이닝 충족 선수만 보기", value=True)
st.sidebar.caption(
    "규정 타석/이닝은 시즌별 경기수에 따라 달라지므로, "
    "여기서는 해당 시즌 상위 요건(타석 상위 70%ile / 이닝 상위 70%ile)을 "
    "간이 기준으로 적용합니다."
)

season_df = df[df["year"] == selected_year].copy()

# ---------------------------------------------------------------
# 타이틀
# ---------------------------------------------------------------
st.title("⚾ KBO 기록 분석 대시보드")
st.caption(f"{selected_year} 시즌 리그 전체 개요")

# ---------------------------------------------------------------
# KPI 메트릭 카드
# ---------------------------------------------------------------
total_players = season_df["player_name"].nunique()

best_avg_row = season_df.loc[season_df["hit_AVG"].idxmax()] if season_df["hit_AVG"].notna().any() else None
most_hr_row = season_df.loc[season_df["hit_HR"].idxmax()] if season_df["hit_HR"].notna().any() else None
best_era_series = season_df[season_df["pit_IP"] >= 30]["pit_ERA"] if "pit_IP" in season_df.columns else season_df["pit_ERA"]
best_era_row = None
if best_era_series is not None and best_era_series.notna().any():
    best_era_idx = best_era_series.idxmin()
    best_era_row = season_df.loc[best_era_idx]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("총 선수 수", f"{total_players:,}명")

with col2:
    if best_avg_row is not None:
        st.metric(
            "최고 타율",
            f"{best_avg_row['hit_AVG']:.3f}",
            help=f"{best_avg_row['player_name']} ({best_avg_row['team']})",
        )
        st.caption(f"🏏 {best_avg_row['player_name']} · {best_avg_row['team']}")
    else:
        st.metric("최고 타율", "N/A")

with col3:
    if most_hr_row is not None:
        st.metric(
            "최다 홈런",
            f"{int(most_hr_row['hit_HR'])}개",
            help=f"{most_hr_row['player_name']} ({most_hr_row['team']})",
        )
        st.caption(f"💣 {most_hr_row['player_name']} · {most_hr_row['team']}")
    else:
        st.metric("최다 홈런", "N/A")

with col4:
    if best_era_row is not None:
        st.metric(
            "최저 ERA (30이닝 이상)",
            f"{best_era_row['pit_ERA']:.2f}",
            help=f"{best_era_row['player_name']} ({best_era_row['team']})",
        )
        st.caption(f"🎯 {best_era_row['player_name']} · {best_era_row['team']}")
    else:
        st.metric("최저 ERA", "N/A")

st.divider()

# ---------------------------------------------------------------
# 규정 타석/이닝 기준 산출 (상위 70%ile 간이 기준)
# ---------------------------------------------------------------
if qualified_only:
    pa_threshold = season_df["hit_PA"].quantile(0.70) if season_df["hit_PA"].notna().any() else 0
    ip_threshold = season_df["pit_IP"].quantile(0.70) if season_df["pit_IP"].notna().any() else 0
else:
    pa_threshold = 0
    ip_threshold = 0

batters = season_df[season_df["hit_PA"] >= pa_threshold].dropna(subset=["hit_AVG", "hit_HR"])
pitchers = season_df[season_df["pit_IP"] >= ip_threshold].dropna(subset=["pit_ERA", "pit_WHIP"])

# ---------------------------------------------------------------
# 산점도: 타율 vs 홈런 / ERA vs WHIP
# ---------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("타율 vs 홈런")
    if not batters.empty:
        fig1 = px.scatter(
            batters,
            x="hit_AVG",
            y="hit_HR",
            color="team",
            size="hit_PA",
            hover_name="player_name",
            hover_data={"hit_AVG": ":.3f", "hit_HR": True, "hit_PA": True, "team": True},
            labels={"hit_AVG": "타율", "hit_HR": "홈런", "team": "구단"},
            color_discrete_sequence=COLOR_SEQUENCE,
        )
        apply_common_layout(fig1, height=460)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("조건을 만족하는 타자 데이터가 없습니다.")

with c2:
    st.subheader("ERA vs WHIP")
    if not pitchers.empty:
        fig2 = px.scatter(
            pitchers,
            x="pit_WHIP",
            y="pit_ERA",
            color="team",
            size="pit_IP",
            hover_name="player_name",
            hover_data={"pit_ERA": ":.2f", "pit_WHIP": ":.2f", "pit_IP": ":.1f", "team": True},
            labels={"pit_WHIP": "WHIP", "pit_ERA": "ERA", "team": "구단"},
            color_discrete_sequence=COLOR_SEQUENCE,
        )
        fig2.update_yaxes(autorange="reversed")  # ERA 낮을수록 우수 -> 상단 배치
        apply_common_layout(fig2, height=460)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("조건을 만족하는 투수 데이터가 없습니다.")

st.divider()
st.caption(
    "📌 좌측 사이드바의 페이지 메뉴에서 선수 상세 분석, 타자/투수 랭킹, "
    "구단 분석, 1:1 선수 비교 페이지로 이동할 수 있습니다."
)
