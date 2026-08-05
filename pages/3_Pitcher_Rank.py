"""
pages/3_Pitcher_Rank.py
-------------------------
투수 분석: 규정이닝 필터, 정렬 가능 테이블, 이닝당 삼진 vs 피안타/피홈런
혼합 차트(Bar+Scatter), 탈삼진-볼넷-ERA 3D 산점도
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.data_loader import load_data, get_years
from utils.style import apply_common_layout, COLOR_SEQUENCE

st.set_page_config(page_title="투수 분석", page_icon="🎯", layout="wide")

df = load_data()
years = get_years(df)

st.title("🎯 투수 분석")

# ---------------------------------------------------------------
# 필터
# ---------------------------------------------------------------
col_a, col_b = st.columns([1, 2])
with col_a:
    selected_year = st.selectbox("시즌 선택", options=years, index=len(years) - 1)

season_df = df[df["year"] == selected_year].copy()
season_df = season_df[season_df["def_POS"] == "투수"].dropna(subset=["pit_IP"])
max_ip = float(season_df["pit_IP"].max()) if not season_df.empty else 0.0

with col_b:
    ip_range = st.slider(
        "규정 이닝(pit_IP) 필터",
        min_value=0.0,
        max_value=max_ip if max_ip > 0 else 1.0,
        value=(round(max_ip * 0.4, 1), max_ip) if max_ip > 0 else (0.0, 1.0),
    )

pitchers = season_df[
    (season_df["pit_IP"] >= ip_range[0]) & (season_df["pit_IP"] <= ip_range[1])
].copy()

st.caption(f"조건을 만족하는 투수: {pitchers['player_name'].nunique()}명")

st.divider()

# ---------------------------------------------------------------
# 정렬 가능한 데이터프레임
# ---------------------------------------------------------------
st.subheader("📋 투수 기록 테이블")

display_cols = [
    "player_name", "team", "pit_IP", "pit_W", "pit_L", "pit_SV", "pit_HLD",
    "pit_ERA", "pit_WHIP", "pit_SO", "pit_BB", "pit_H", "pit_HR",
]
display_cols = [c for c in display_cols if c in pitchers.columns]

st.dataframe(
    pitchers[display_cols].sort_values("pit_ERA", ascending=True),
    use_container_width=True,
    hide_index=True,
    column_config={
        "pit_IP": st.column_config.NumberColumn("이닝(IP)", format="%.1f"),
        "pit_ERA": st.column_config.NumberColumn("ERA", format="%.2f"),
        "pit_WHIP": st.column_config.NumberColumn("WHIP", format="%.2f"),
    },
)

st.divider()

# ---------------------------------------------------------------
# 혼합 차트: 이닝당 삼진비율(K9, Bar) + 피안타/피홈런 합계(Scatter)
# ---------------------------------------------------------------
st.subheader("📊 이닝당 삼진율 vs 피안타·피홈런 (혼합 차트)")

mix_df = pitchers.dropna(subset=["pit_K9"]).copy()
mix_df = mix_df.sort_values("pit_K9", ascending=False).head(20)

if not mix_df.empty:
    fig_mix = make_subplots(specs=[[{"secondary_y": True}]])

    fig_mix.add_trace(
        go.Bar(
            x=mix_df["player_name"],
            y=mix_df["pit_K9"],
            name="이닝당 삼진(K9)",
            marker_color=COLOR_SEQUENCE[0],
        ),
        secondary_y=False,
    )
    fig_mix.add_trace(
        go.Scatter(
            x=mix_df["player_name"],
            y=mix_df["pit_H"],
            name="피안타(H)",
            mode="lines+markers",
            line=dict(color=COLOR_SEQUENCE[1], width=2),
        ),
        secondary_y=True,
    )
    fig_mix.add_trace(
        go.Scatter(
            x=mix_df["player_name"],
            y=mix_df["pit_HR"],
            name="피홈런(HR)",
            mode="lines+markers",
            line=dict(color=COLOR_SEQUENCE[3], width=2, dash="dot"),
        ),
        secondary_y=True,
    )

    fig_mix.update_yaxes(title_text="K9 (이닝당 삼진)", secondary_y=False)
    fig_mix.update_yaxes(title_text="피안타 / 피홈런 (개)", secondary_y=True)
    fig_mix.update_xaxes(tickangle=-40)
    apply_common_layout(fig_mix, title="K9 상위 20명 기준", height=520)
    st.plotly_chart(fig_mix, use_container_width=True)
else:
    st.info("표시할 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# 3D 산점도: 탈삼진 vs 볼넷 vs ERA
# ---------------------------------------------------------------
st.subheader("🌐 투수 구위 분석 (3D: 탈삼진 · 볼넷 · ERA)")

three_d_df = pitchers.dropna(subset=["pit_SO", "pit_BB", "pit_ERA"])

if not three_d_df.empty:
    fig_3d = px.scatter_3d(
        three_d_df,
        x="pit_SO",
        y="pit_BB",
        z="pit_ERA",
        color="team",
        size="pit_IP",
        hover_name="player_name",
        labels={"pit_SO": "탈삼진(SO)", "pit_BB": "볼넷(BB)", "pit_ERA": "ERA"},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig_3d.update_scenes(zaxis_autorange="reversed")  # ERA는 낮을수록 우수
    apply_common_layout(fig_3d, height=600)
    fig_3d.update_layout(scene=dict(
        xaxis_title="탈삼진(SO)", yaxis_title="볼넷(BB)", zaxis_title="ERA",
    ))
    st.plotly_chart(fig_3d, use_container_width=True)
else:
    st.info("3D 차트를 그릴 데이터가 부족합니다.")
