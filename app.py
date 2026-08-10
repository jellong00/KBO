"""
app.py
--------
🏠 홈: 데이터 소개
수업 도입부용 페이지. "이 데이터가 뭔지"를 카드/표/간단한 시각화로 보여줌.
"""

import streamlit as st
import plotly.graph_objects as go

from utils.data_loader import load_data, get_years, get_teams
from utils.style import apply_common_layout, COLOR_SEQUENCE

st.set_page_config(page_title="KBO 데이터 대시보드", page_icon="⚾", layout="wide")

df = load_data()
years = get_years(df)
teams = get_teams(df)

st.title("⚾ KBO 리그 데이터 대시보드")
st.caption("2001~2025 시즌, 선수 개인 기록 데이터를 활용한 야구 통계 탐색 · 교육용 대시보드")

st.divider()

# ---------------------------------------------------------------
# 기본 정보 카드
# ---------------------------------------------------------------
st.subheader("📦 데이터 한눈에 보기")

c1, c2, c3, c4 = st.columns(4)
c1.metric("전체 관측치(선수-시즌)", f"{len(df):,}건")
c2.metric("등록 선수 수", f"{df['player_id'].nunique():,}명")
c3.metric("시즌 범위", f"{years[0]} ~ {years[-1]}", help=f"{len(years)}개 시즌")
c4.metric("구단 수(역대 명칭 포함)", f"{len(teams)}개")

st.divider()

# ---------------------------------------------------------------
# 데이터 구조 설명
# ---------------------------------------------------------------
st.subheader("🗂️ 데이터 구조")

col_left, col_right = st.columns([1.3, 1])

with col_left:
    st.markdown("""
이 데이터는 **선수 한 명이 한 시즌 동안 기록한 성적 한 줄**을 기본 단위로 합니다.
컬럼은 크게 4개 그룹으로 나뉩니다.

| 그룹 | 접두어 | 예시 컬럼 | 설명 |
|---|---|---|---|
| 타격 | `hit_` | hit_AVG, hit_HR, hit_OPS | 타자로서 남긴 기록 |
| 투구 | `pit_` | pit_ERA, pit_WHIP, pit_SO | 투수로서 남긴 기록 |
| 수비 | `def_` | def_G, def_FPCT | 포지션별 수비 기록 |
| 주루 | `run_` | run_SB, run_SB_pct | 도루 등 주루 기록 |

⚠️ 한 선수가 투수이면서 타석에 서거나(투수 타격), 여러 포지션을 겸하는 경우도 있어서
`hit_*`/`pit_*` 컬럼이 동시에 값을 가질 수 있습니다. "이 선수가 투수인가 타자인가"는
`primary_position` 컬럼(그 시즌 가장 많이 뛴 포지션) 기준으로 판단하시면 됩니다.
    """)
    
st.divider()

# ---------------------------------------------------------------
# 구단 변천사 시각화 (프랜차이즈 히스토리)
# ---------------------------------------------------------------
st.subheader("🏟️ 구단 변천사")
st.caption("각 팀명이 어느 시즌까지 데이터에 존재하는지 보여줍니다. 팀 분석 시 이름이 바뀐 구단은 같은 팀으로 봐야 함을 알 수 있습니다.")

team_span = (
    df.groupby("team")["year"].agg(["min", "max"]).reset_index()
    .sort_values("min")
)

fig_span = go.Figure()
for i, row in team_span.iterrows():
    fig_span.add_trace(go.Scatter(
        x=[row["min"], row["max"]], y=[row["team"], row["team"]],
        mode="lines+markers",
        line=dict(color=COLOR_SEQUENCE[i % len(COLOR_SEQUENCE)], width=8),
        marker=dict(size=10),
        showlegend=False,
    ))
fig_span.update_xaxes(title="연도", dtick=2)
fig_span.update_yaxes(title="")
apply_common_layout(fig_span, height=420)
st.plotly_chart(fig_span, use_container_width=True)

st.divider()

# ---------------------------------------------------------------
# 연도별 등록 선수 수 (리그 확장 추이)
# ---------------------------------------------------------------
st.subheader("📈 연도별 등록 선수 수")
st.caption("리그에 참여한 구단 수가 늘어나며(8개→10개) 등록 선수 수도 함께 늘어난 것을 볼 수 있습니다.")

player_count = df.groupby("year")["player_id"].nunique().reset_index()
fig_count = go.Figure(go.Bar(
    x=player_count["year"], y=player_count["player_id"],
    marker_color=COLOR_SEQUENCE[0],
))
fig_count.update_xaxes(title="연도", dtick=2)
fig_count.update_yaxes(title="등록 선수 수(명)")
apply_common_layout(fig_count, height=380)
st.plotly_chart(fig_count, use_container_width=True)

st.divider()
st.markdown("### 👈 왼쪽 사이드바에서 다른 페이지로 이동해서 더 자세한 분석을 확인해보세요.")
