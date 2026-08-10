"""
pages/3_랭킹.py
------------------
🏆 랭킹: 타자 탭 / 투수 탭 
- 규정 타석/이닝 필터, 순위 테이블
- 타자: 세이버메트릭스 히트맵 1개만
- 투수: K9 vs 피안타/피홈런 혼합차트 1개만
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.data_loader import load_data, get_years
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import render_glossary

st.set_page_config(page_title="랭킹", page_icon="🏆", layout="wide")

df = load_data()
years = get_years(df)

st.title("🏆 랭킹")

tab_batter, tab_pitcher = st.tabs(["🏏 타자 랭킹", "🎯 투수 랭킹"])

# =================================================================
# 타자 탭
# =================================================================
with tab_batter:
    render_glossary(["hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS", "hit_RISP"])

    col_a, col_b = st.columns([1, 2])
    with col_a:
        b_year = st.selectbox("시즌 선택", options=years, index=len(years) - 1, key="b_year")

    b_season = df[df["year"] == b_year].copy()
    max_pa = int(b_season["hit_PA"].max()) if b_season["hit_PA"].notna().any() else 0

    with col_b:
        pa_range = st.slider(
            "규정 타석(hit_PA) 필터", min_value=0,
            max_value=max_pa if max_pa > 0 else 1,
            value=(int(max_pa * 0.5), max_pa) if max_pa > 0 else (0, 1),
            key="pa_range",
        )

    batters = b_season[(b_season["hit_PA"] >= pa_range[0]) & (b_season["hit_PA"] <= pa_range[1])].copy()
    batters = batters.dropna(subset=["hit_AVG"])
    st.caption(f"조건을 만족하는 타자: {batters['player_name'].nunique()}명")

    st.divider()
    st.subheader("📋 타자 기록 테이블")

    rank_options = {
        "OPS 높은순": ("hit_OPS", False), "타율 높은순": ("hit_AVG", False),
        "홈런 많은순": ("hit_HR", False), "이름(가나다순)": ("player_name", True),
    }
    sort_choice = st.selectbox("정렬 기준", options=list(rank_options.keys()), key="b_sort")
    rank_col, is_alpha = rank_options[sort_choice]

    table_df = batters.copy()
    table_df["종합순위"] = table_df["hit_OPS"].rank(ascending=False, method="min").astype("Int64")
    table_df = table_df.sort_values("player_name") if is_alpha else table_df.sort_values(rank_col, ascending=False)

    display_cols = ["종합순위", "player_name", "team", "primary_position", "hit_PA", "hit_AB", "hit_H",
                     "hit_2B", "hit_3B", "hit_HR", "hit_RBI", "hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS"]
    display_cols = [c for c in display_cols if c in table_df.columns]
    st.dataframe(
        table_df[display_cols], use_container_width=True, hide_index=True,
        column_config={
            "종합순위": st.column_config.NumberColumn("종합순위(OPS 기준)"),
            "player_name": st.column_config.TextColumn("선수명"),
            "team": st.column_config.TextColumn("구단"),
            "primary_position": st.column_config.TextColumn("주포지션"),
            "hit_AVG": st.column_config.NumberColumn("타율", format="%.3f"),
            "hit_OBP": st.column_config.NumberColumn("출루율", format="%.3f"),
            "hit_SLG": st.column_config.NumberColumn("장타율", format="%.3f"),
            "hit_OPS": st.column_config.NumberColumn("OPS", format="%.3f"),
        },
    )

    st.divider()
    st.subheader("💠 세이버메트릭스 히트맵 (OPS 상위 15명)")

    metric_cols = ["hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS", "hit_RISP"]
    metric_labels = ["타율", "출루율", "장타율", "OPS", "득점권타율"]
    heat_src = batters.dropna(subset=["hit_OPS"]).sort_values("hit_OPS", ascending=False).head(15)

    if not heat_src.empty:
        z_raw = heat_src[metric_cols].to_numpy(dtype=float)
        col_means = np.nanmean(z_raw, axis=0)
        z_filled = np.where(np.isnan(z_raw), col_means, z_raw)
        col_min, col_max = z_filled.min(axis=0), z_filled.max(axis=0)
        z_norm = (z_filled - col_min) / (col_max - col_min + 1e-9)
        text_matrix = np.array([[f"{v:.3f}" if not np.isnan(v) else "-" for v in row] for row in z_raw])

        fig_heat = go.Figure(go.Heatmap(
            z=z_norm.T, x=heat_src["player_name"], y=metric_labels,
            text=text_matrix.T, texttemplate="%{text}", textfont=dict(color="#111827", size=12),
            colorscale="RdYlGn", showscale=False, xgap=3, ygap=3,
        ))
        fig_heat.update_xaxes(tickangle=-40)
        apply_common_layout(fig_heat, title="선수(열) × 지표(행) — 초록에 가까울수록 상위권", height=380)
        st.plotly_chart(fig_heat, use_container_width=True, theme=None)
    else:
        st.info("표시할 데이터가 부족합니다.")

# =================================================================
# 투수 탭
# =================================================================
with tab_pitcher:
    render_glossary(["pit_ERA", "pit_WHIP", "pit_IP", "pit_K9", "pit_SO", "pit_BB"])

    col_a, col_b = st.columns([1, 2])
    with col_a:
        p_year = st.selectbox("시즌 선택", options=years, index=len(years) - 1, key="p_year")

    p_season = df[df["year"] == p_year].copy()
    p_season = p_season[p_season["primary_position"] == "투수"].dropna(subset=["pit_IP"])
    max_ip = float(p_season["pit_IP"].max()) if not p_season.empty else 0.0

    with col_b:
        ip_range = st.slider(
            "규정 이닝(pit_IP) 필터", min_value=0.0,
            max_value=max_ip if max_ip > 0 else 1.0,
            value=(round(max_ip * 0.4, 1), max_ip) if max_ip > 0 else (0.0, 1.0),
            key="ip_range",
        )

    pitchers = p_season[(p_season["pit_IP"] >= ip_range[0]) & (p_season["pit_IP"] <= ip_range[1])].copy()
    st.caption(f"조건을 만족하는 투수: {pitchers['player_name'].nunique()}명")

    st.divider()
    st.subheader("📋 투수 기록 테이블")

    rank_options_p = {
        "ERA 낮은순": ("pit_ERA", False, True), "WHIP 낮은순": ("pit_WHIP", False, True),
        "탈삼진 많은순": ("pit_SO", False, False), "승수 많은순": ("pit_W", False, False),
        "이름(가나다순)": ("player_name", True, True),
    }
    sort_choice_p = st.selectbox("정렬 기준", options=list(rank_options_p.keys()), key="p_sort")
    rank_col, is_alpha, ascending = rank_options_p[sort_choice_p]

    table_df_p = pitchers.copy()
    table_df_p["종합순위"] = table_df_p["pit_ERA"].rank(ascending=True, method="min").astype("Int64")
    table_df_p = table_df_p.sort_values("player_name") if is_alpha else table_df_p.sort_values(rank_col, ascending=ascending)

    display_cols_p = ["종합순위", "player_name", "team", "pit_IP", "pit_W", "pit_L", "pit_SV", "pit_HLD",
                       "pit_ERA", "pit_WHIP", "pit_SO", "pit_BB", "pit_H", "pit_HR"]
    display_cols_p = [c for c in display_cols_p if c in table_df_p.columns]
    st.dataframe(
        table_df_p[display_cols_p], use_container_width=True, hide_index=True,
        column_config={
            "종합순위": st.column_config.NumberColumn("종합순위(ERA 기준)"),
            "player_name": st.column_config.TextColumn("선수명"),
            "team": st.column_config.TextColumn("구단"),
            "pit_IP": st.column_config.NumberColumn("이닝(IP)", format="%.1f"),
            "pit_ERA": st.column_config.NumberColumn("ERA", format="%.2f"),
            "pit_WHIP": st.column_config.NumberColumn("WHIP", format="%.2f"),
        },
    )

    st.divider()
    st.subheader("📊 이닝당 삼진율 vs 피안타·피홈런 (혼합 차트)")

    mix_df = pitchers.dropna(subset=["pit_K9"]).copy().sort_values("pit_K9", ascending=False).head(20)
    if not mix_df.empty:
        fig_mix = make_subplots(specs=[[{"secondary_y": True}]])
        fig_mix.add_trace(go.Bar(x=mix_df["player_name"], y=mix_df["pit_K9"], name="이닝당 삼진(K9)",
                                  marker_color=COLOR_SEQUENCE[0]), secondary_y=False)
        fig_mix.add_trace(go.Scatter(x=mix_df["player_name"], y=mix_df["pit_H"], name="피안타(H)",
                                      mode="lines+markers", line=dict(color=COLOR_SEQUENCE[1], width=2)), secondary_y=True)
        fig_mix.add_trace(go.Scatter(x=mix_df["player_name"], y=mix_df["pit_HR"], name="피홈런(HR)",
                                      mode="lines+markers", line=dict(color=COLOR_SEQUENCE[3], width=2, dash="dot")), secondary_y=True)
        fig_mix.update_yaxes(title_text="K9", secondary_y=False)
        fig_mix.update_yaxes(title_text="피안타 / 피홈런", secondary_y=True)
        fig_mix.update_xaxes(tickangle=-40)
        apply_common_layout(fig_mix, title="K9 상위 20명 기준", height=520)
        st.plotly_chart(fig_mix, use_container_width=True, theme=None)
    else:
        st.info("표시할 데이터가 부족합니다.")
