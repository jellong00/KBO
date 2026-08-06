"""
app.py
------
KBO 기록 분석 대시보드 - 메인 홈
실행: streamlit run app.py
"""

import streamlit as st
import plotly.graph_objects as go

from utils.data_loader import load_data, get_years
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import render_glossary

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

# ERA(평균자책점), WHIP 등 약어가 낯설 수 있으므로 화면에도 설명을 노출
render_glossary(["hit_AVG", "hit_HR", "pit_ERA", "pit_WHIP"])

# ---------------------------------------------------------------
# KPI 메트릭 카드
# ---------------------------------------------------------------
total_players = season_df["player_name"].nunique()

# hit_AVG(타율) = 안타/타수, hit_HR(홈런) = 시즌 홈런 개수
best_avg_row = season_df.loc[season_df["hit_AVG"].idxmax()] if season_df["hit_AVG"].notna().any() else None
most_hr_row = season_df.loc[season_df["hit_HR"].idxmax()] if season_df["hit_HR"].notna().any() else None
# pit_ERA(평균자책점, Earned Run Average) = 9이닝당 자책점. 낮을수록 우수.
# 이닝이 너무 적은 투수가 우연히 낮은 ERA로 뽑히는 것을 막기 위해 30이닝 이상만 집계.
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
# 리더보드: 타율 Top 10 / ERA Top 10 (막대그래프)
# 기존에는 산점도(타율 vs 홈런, ERA vs WHIP)로 관계를 보여줬으나,
# 점이 많으면 한눈에 들어오지 않는다는 피드백에 따라 순위가 명확히 보이는
# 가로 막대 리더보드로 교체. 보조 지표(홈런/WHIP)는 막대 끝 텍스트로 함께 표기.
# ---------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("🏏 타율 Top 10 (규정 타석 기준)")
    if not batters.empty:
        top_avg = batters.sort_values("hit_AVG", ascending=False).head(10).sort_values("hit_AVG")
        fig1 = go.Figure(go.Bar(
            x=top_avg["hit_AVG"],
            y=top_avg["player_name"],
            orientation="h",
            marker_color=COLOR_SEQUENCE[0],
            text=[f"{avg:.3f} · HR {int(hr)}" for avg, hr in zip(top_avg["hit_AVG"], top_avg["hit_HR"])],
            textposition="outside",
        ))
        fig1.update_xaxes(title="타율")
        fig1.update_layout(margin=dict(r=140))
        apply_common_layout(fig1, height=460)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("조건을 만족하는 타자 데이터가 없습니다.")

with c2:
    st.subheader("🎯 ERA Top 10 (규정 이닝 기준)")
    # pit_WHIP (Walks+Hits per Inning Pitched) = 이닝당 허용 안타+볼넷. 낮을수록 좋음.
    # ERA는 낮을수록 우수하므로 오름차순 정렬 후 상위 10명을 뽑는다.
    if not pitchers.empty:
        top_era = pitchers.sort_values("pit_ERA", ascending=True).head(10).sort_values("pit_ERA", ascending=False)
        fig2 = go.Figure(go.Bar(
            x=top_era["pit_ERA"],
            y=top_era["player_name"],
            orientation="h",
            marker_color=COLOR_SEQUENCE[3],
            text=[f"{era:.2f} · WHIP {whip:.2f}" for era, whip in zip(top_era["pit_ERA"], top_era["pit_WHIP"])],
            textposition="outside",
        ))
        fig2.update_xaxes(title="ERA")
        fig2.update_layout(margin=dict(r=140))
        apply_common_layout(fig2, height=460)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("조건을 만족하는 투수 데이터가 없습니다.")

st.divider()
st.caption(
    "📌 좌측 사이드바의 페이지 메뉴에서 선수 상세 분석, 타자/투수 랭킹, "
    "구단 분석, 1:1 선수 비교 페이지로 이동할 수 있습니다."
)
