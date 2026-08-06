"""
pages/4_Team_Analysis.py
--------------------------
구단 분석 (전면 개편):
  ① 팀 타격 스타일 사분면 (홈런 vs 도루) - 빅볼 vs 스몰볼 구단 분류
  ② 팀 투·타 밸런스 사분면 (팀 OPS vs 팀 ERA) - 구단 전력 유형 분류
  ③ 팀 수비·주루 효율성 레이더 (선택 구단 vs 리그 평균)
  ④ 팀 내 기여도 트리맵 (선택 구단 로스터의 특정 기록 기여도 - 원맨팀 vs 고른 활약)
+ 요약 지표, Top5 승리기여투수/홈런타자
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.data_loader import load_data, get_years, get_teams
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import render_glossary

st.set_page_config(page_title="구단 분석", page_icon="🏟️", layout="wide")

df = load_data()
years = get_years(df)

st.title("🏟️ 구단 분석")
render_glossary(["hit_AVG", "hit_HR", "pit_ERA", "pit_W", "def_FPCT", "run_SB_pct"])

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
pitchers_team = team_df[team_df["def_POS"].str.contains("투수", na=False)].dropna(subset=["pit_ERA"])

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
# Top 5 승리 기여 투수 / Top 5 홈런 타자
# ---------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("🏆 승리 기여 투수 Top 5")
    win_df = pitchers_team.drop_duplicates(subset=["player_name"]).copy()
    if "pit_W" in win_df.columns and not win_df.empty:
        win_df["contribution"] = (
            win_df["pit_W"].fillna(0)
            + 0.5 * win_df.get("pit_HLD", 0).fillna(0)
            + 0.7 * win_df.get("pit_SV", 0).fillna(0)
        )
        top5_pitchers = win_df.sort_values("contribution", ascending=False).head(5)
        fig_p = px.bar(
            top5_pitchers.sort_values("contribution"),
            x="contribution", y="player_name", orientation="h", text="contribution",
            labels={"contribution": "승리 기여도(가중)", "player_name": "선수"},
            color_discrete_sequence=[COLOR_SEQUENCE[0]],
        )
        fig_p.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        apply_common_layout(fig_p, height=380)
        st.plotly_chart(fig_p, use_container_width=True)
        st.caption("승리 기여도 = 승수 + 0.5×홀드 + 0.7×세이브 (간이 가중치 기준)")
    else:
        st.info("투수 데이터가 부족합니다.")

with c2:
    st.subheader("💣 홈런 타자 Top 5")
    hr_df = batters_team.dropna(subset=["hit_HR"]).drop_duplicates(subset=["player_name"])
    if not hr_df.empty:
        top5_batters = hr_df.sort_values("hit_HR", ascending=False).head(5)
        fig_b = px.bar(
            top5_batters.sort_values("hit_HR"),
            x="hit_HR", y="player_name", orientation="h", text="hit_HR",
            labels={"hit_HR": "홈런", "player_name": "선수"},
            color_discrete_sequence=[COLOR_SEQUENCE[3]],
        )
        fig_b.update_traces(texttemplate="%{text}", textposition="outside")
        apply_common_layout(fig_b, height=380)
        st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.info("타자 데이터가 부족합니다.")

st.divider()

# =================================================================
# 구단 단위(팀 레벨) 집계 준비 - 아래 ①~④ 섹션에서 공통으로 사용
# =================================================================
team_batters_all = season_df.dropna(subset=["hit_AVG"])
team_pitchers_all = season_df[season_df["def_POS"].str.contains("투수", na=False)].dropna(subset=["pit_ERA"])

team_stats = pd.DataFrame({
    "team": teams,
    "팀총홈런": [team_batters_all[team_batters_all["team"] == t]["hit_HR"].sum() for t in teams],
    "팀총도루": [team_batters_all[team_batters_all["team"] == t]["run_SB"].sum() for t in teams],
    "팀평균OPS": [team_batters_all[team_batters_all["team"] == t]["hit_OPS_est"].mean() for t in teams],
    "팀평균ERA": [team_pitchers_all[team_pitchers_all["team"] == t]["pit_ERA"].mean() for t in teams],
})

# ---------------------------------------------------------------
# ① 팀 타격 스타일 사분면 (홈런 vs 도루) - 빅볼 vs 스몰볼
# ---------------------------------------------------------------
st.subheader("① 팀 타격 스타일 사분면 (홈런 vs 도루)")
st.caption("오른쪽으로 갈수록 '뛰는 야구'(스몰볼), 위로 갈수록 '장타 야구'(빅볼) 성향의 구단입니다.")

style_df = team_stats.dropna(subset=["팀총홈런", "팀총도루"])
if not style_df.empty:
    avg_hr = style_df["팀총홈런"].mean()
    avg_sb = style_df["팀총도루"].mean()
    colors1 = [COLOR_SEQUENCE[1] if t == selected_team else "#94A3B8" for t in style_df["team"]]

    fig_style = go.Figure(go.Scatter(
        x=style_df["팀총도루"], y=style_df["팀총홈런"],
        mode="markers+text", text=style_df["team"], textposition="top center",
        marker=dict(size=16, color=colors1, line=dict(width=1, color="white")),
    ))
    fig_style.add_vline(x=avg_sb, line_dash="dash", line_color="#CBD5E1")
    fig_style.add_hline(y=avg_hr, line_dash="dash", line_color="#CBD5E1")
    fig_style.add_annotation(x=style_df["팀총도루"].max(), y=style_df["팀총홈런"].max(), text="파워&스피드형", showarrow=False, font=dict(color="#94A3B8", size=11), xanchor="right")
    fig_style.add_annotation(x=style_df["팀총도루"].min(), y=style_df["팀총홈런"].max(), text="빅볼(장타)형", showarrow=False, font=dict(color="#94A3B8", size=11), xanchor="left")
    fig_style.add_annotation(x=style_df["팀총도루"].max(), y=style_df["팀총홈런"].min(), text="스몰볼(주루)형", showarrow=False, font=dict(color="#94A3B8", size=11), xanchor="right")
    fig_style.add_annotation(x=style_df["팀총도루"].min(), y=style_df["팀총홈런"].min(), text="빈타/저조형", showarrow=False, font=dict(color="#94A3B8", size=11), xanchor="left")
    fig_style.update_xaxes(title="팀 총 도루")
    fig_style.update_yaxes(title="팀 총 홈런")
    apply_common_layout(fig_style, height=480)
    st.plotly_chart(fig_style, use_container_width=True)
else:
    st.info("도루 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# ② 팀 투·타 밸런스 사분면 (팀 OPS vs 팀 ERA)
# ---------------------------------------------------------------
st.subheader("② 팀 투·타 밸런스 사분면 (팀 OPS vs 팀 ERA)")
st.caption("오른쪽 위로 갈수록 공격력(OPS)이 높고 방어력(ERA, 낮을수록 좋음)도 우수한 '투타 밸런스형' 강팀입니다.")

balance_df = team_stats.dropna(subset=["팀평균OPS", "팀평균ERA"])
if not balance_df.empty:
    avg_ops = balance_df["팀평균OPS"].mean()
    avg_era = balance_df["팀평균ERA"].mean()
    colors2 = [COLOR_SEQUENCE[1] if t == selected_team else "#94A3B8" for t in balance_df["team"]]

    fig_balance = go.Figure(go.Scatter(
        x=balance_df["팀평균OPS"], y=balance_df["팀평균ERA"],
        mode="markers+text", text=balance_df["team"], textposition="top center",
        marker=dict(size=16, color=colors2, line=dict(width=1, color="white")),
    ))
    fig_balance.add_vline(x=avg_ops, line_dash="dash", line_color="#CBD5E1")
    fig_balance.add_hline(y=avg_era, line_dash="dash", line_color="#CBD5E1")
    fig_balance.update_yaxes(title="팀 평균 ERA (방어력)", autorange="reversed")  # ERA 낮을수록 위(우수)
    fig_balance.update_xaxes(title="팀 평균 OPS (공격력)")
    y_top = balance_df["팀평균ERA"].min()
    y_bot = balance_df["팀평균ERA"].max()
    fig_balance.add_annotation(x=balance_df["팀평균OPS"].max(), y=y_top, text="투타 밸런스 우수", showarrow=False, font=dict(color="#94A3B8", size=11), xanchor="right", yanchor="bottom")
    fig_balance.add_annotation(x=balance_df["팀평균OPS"].min(), y=y_top, text="투수력 의존형", showarrow=False, font=dict(color="#94A3B8", size=11), xanchor="left", yanchor="bottom")
    fig_balance.add_annotation(x=balance_df["팀평균OPS"].max(), y=y_bot, text="타력 의존형", showarrow=False, font=dict(color="#94A3B8", size=11), xanchor="right", yanchor="top")
    fig_balance.add_annotation(x=balance_df["팀평균OPS"].min(), y=y_bot, text="약팀형", showarrow=False, font=dict(color="#94A3B8", size=11), xanchor="left", yanchor="top")
    apply_common_layout(fig_balance, height=480)
    st.plotly_chart(fig_balance, use_container_width=True)
else:
    st.info("팀 OPS/ERA 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# ③ 팀 수비·주루 효율성 레이더 (선택 구단 vs 리그 평균)
# ---------------------------------------------------------------
st.subheader("③ 팀 수비·주루 효율성 레이더 (선택 구단 vs 리그 평균)")

radar_metrics = {
    "타율": "hit_AVG", "출루율": "hit_OBP_est", "장타율": "hit_SLG",
    "수비율": "def_FPCT", "도루성공률": "run_SB_pct",
}

league_vals, team_vals, labels = [], [], []
for label, col in radar_metrics.items():
    if col == "def_FPCT":
        league_series = season_df.dropna(subset=[col])[col]
        team_series = team_df.dropna(subset=[col])[col]
    elif col == "run_SB_pct":
        league_series = season_df.dropna(subset=[col])[col]
        team_series = team_df.dropna(subset=[col])[col]
    else:
        league_series = team_batters_all.dropna(subset=[col])[col]
        team_series = batters_team.dropna(subset=[col])[col]
    if league_series.empty:
        continue
    league_mean = league_series.mean()
    team_mean = team_series.mean() if not team_series.empty else np.nan
    # 리그 평균 대비 백분위(0~100, 50=리그평균)로 정규화
    pct = (league_series < team_mean).sum() / len(league_series) * 100 if pd.notna(team_mean) else 0
    labels.append(label)
    team_vals.append(round(pct, 1))
    league_vals.append(50)

if labels:
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=league_vals + [league_vals[0]], theta=labels + [labels[0]],
        name="리그 평균", line=dict(color="#94A3B8", width=2, dash="dot"), fill="none",
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=team_vals + [team_vals[0]], theta=labels + [labels[0]],
        name=selected_team, line=dict(color=COLOR_SEQUENCE[1], width=2),
        fillcolor="rgba(249, 115, 22, 0.25)", fill="toself",
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%", tickfont=dict(color="#374151")),
            angularaxis=dict(tickfont=dict(color="#111827", size=12)),
        ),
    )
    apply_common_layout(fig_radar, title=f"{selected_team} vs 리그 평균 (백분위)", height=500)
    st.plotly_chart(fig_radar, use_container_width=True)
    st.caption("50%가 리그 평균선입니다. 바깥으로 나갈수록 해당 지표에서 리그 상위권이라는 뜻입니다.")
else:
    st.info("레이더 차트를 계산할 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# ④ 팀 내 기여도 트리맵 (원맨팀 vs 고른 활약)
# ---------------------------------------------------------------
st.subheader("④ 팀 내 기여도 트리맵 (원맨팀 vs 고른 활약)")

treemap_metric_options = {"홈런": "hit_HR", "안타": "hit_H", "타점": "hit_RBI"}
treemap_metric_label = st.radio("기여도 기준", options=list(treemap_metric_options.keys()), horizontal=True)
treemap_col = treemap_metric_options[treemap_metric_label]

tree_df = batters_team.dropna(subset=[treemap_col])
tree_df = tree_df[tree_df[treemap_col] > 0]

if not tree_df.empty:
    fig_tree = px.treemap(
        tree_df,
        path=[px.Constant(f"{selected_team} 전체"), "player_name"],
        values=treemap_col,
        color=treemap_col,
        color_continuous_scale="Blues",
    )
    fig_tree.update_traces(textinfo="label+value+percent parent")
    apply_common_layout(fig_tree, title=f"{selected_team} {selected_year} — {treemap_metric_label} 기여도", height=520)
    st.plotly_chart(fig_tree, use_container_width=True)
    top_share = tree_df.sort_values(treemap_col, ascending=False).iloc[0]
    top_pct = top_share[treemap_col] / tree_df[treemap_col].sum() * 100
    st.caption(f"{top_share['player_name']} 선수 한 명이 팀 전체 {treemap_metric_label}의 {top_pct:.1f}%를 차지합니다. 이 비중이 크면 '원맨팀'에 가깝고, 여러 선수에게 고르게 분산되어 있으면 '고른 활약' 팀입니다.")
else:
    st.info("표시할 데이터가 부족합니다.")
