"""
pages/4_Team_Analysis.py
--------------------------
구단 분석: 구단 선택 필터, 요약 지표, Top5 투수/타자 가로 막대 그래프
"""

import streamlit as st
import plotly.express as px

from utils.data_loader import load_data, get_years, get_teams
from utils.style import apply_common_layout, COLOR_SEQUENCE

st.set_page_config(page_title="구단 분석", page_icon="🏟️", layout="wide")

df = load_data()
years = get_years(df)

st.title("🏟️ 구단 분석")

col_a, col_b = st.columns(2)
with col_a:
    selected_year = st.selectbox("시즌 선택", options=years, index=len(years) - 1)

season_df = df[df["year"] == selected_year].copy()
teams = get_teams(season_df)

with col_b:
    selected_team = st.selectbox("구단 선택", options=teams)

team_df = season_df[season_df["team"] == selected_team].copy()

st.divider()

# ---------------------------------------------------------------
# 구단 요약 지표
# ---------------------------------------------------------------
st.subheader(f"📌 {selected_team} {selected_year} 시즌 요약")

batters_team = team_df.dropna(subset=["hit_AVG"])
pitchers_team = team_df[team_df["def_POS"] == "투수"].dropna(subset=["pit_ERA"])

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("팀 평균 타율", f"{batters_team['hit_AVG'].mean():.3f}" if not batters_team.empty else "N/A")
with col2:
    st.metric("팀 총 홈런", f"{int(batters_team['hit_HR'].sum()):,}개" if not batters_team.empty else "N/A")
with col3:
    st.metric("팀 평균 ERA", f"{pitchers_team['pit_ERA'].mean():.2f}" if not pitchers_team.empty else "N/A")
with col4:
    st.metric("등록 선수 수", f"{team_df['player_name'].nunique()}명")

st.divider()

# ---------------------------------------------------------------
# Top 5 승리 기여 투수 / Top 5 홈런 타자 (가로 막대)
# ---------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("🏆 승리 기여 투수 Top 5")
    win_df = pitchers_team.copy()
    if "pit_W" in win_df.columns and not win_df.empty:
        # 승리 기여도 = 승수 + 0.5 * 홀드 + 0.7 * 세이브 (간이 가중치)
        win_df["contribution"] = (
            win_df["pit_W"].fillna(0)
            + 0.5 * win_df.get("pit_HLD", 0).fillna(0)
            + 0.7 * win_df.get("pit_SV", 0).fillna(0)
        )
        top5_pitchers = win_df.sort_values("contribution", ascending=False).head(5)
        fig_p = px.bar(
            top5_pitchers.sort_values("contribution"),
            x="contribution",
            y="player_name",
            orientation="h",
            text="contribution",
            labels={"contribution": "승리 기여도(가중)", "player_name": "선수"},
            color_discrete_sequence=[COLOR_SEQUENCE[0]],
        )
        fig_p.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        apply_common_layout(fig_p, height=420)
        st.plotly_chart(fig_p, use_container_width=True)
        st.caption("승리 기여도 = 승수 + 0.5×홀드 + 0.7×세이브 (간이 가중치 기준)")
    else:
        st.info("투수 데이터가 부족합니다.")

with c2:
    st.subheader("💣 홈런 타자 Top 5")
    hr_df = batters_team.dropna(subset=["hit_HR"])
    if not hr_df.empty:
        top5_batters = hr_df.sort_values("hit_HR", ascending=False).head(5)
        fig_b = px.bar(
            top5_batters.sort_values("hit_HR"),
            x="hit_HR",
            y="player_name",
            orientation="h",
            text="hit_HR",
            labels={"hit_HR": "홈런", "player_name": "선수"},
            color_discrete_sequence=[COLOR_SEQUENCE[3]],
        )
        fig_b.update_traces(texttemplate="%{text}", textposition="outside")
        apply_common_layout(fig_b, height=420)
        st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.info("타자 데이터가 부족합니다.")

with st.expander("📋 구단 전체 선수 기록 보기"):
    st.dataframe(team_df, use_container_width=True, hide_index=True)
