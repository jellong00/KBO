"""
pages/4_랭킹.py
------------------
🏆 랭킹: 타자 탭 / 투수 탭 (최종 간소화 버전)
- 최소 타석·이닝 필터
- 순위 테이블
- 지표 선택 -> Top 10 가로 막대그래프 (딱 이거 하나만)
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

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
    render_glossary(["hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS"])

    col_a, col_b = st.columns([1, 2])
    with col_a:
        b_year = st.selectbox("시즌 선택", options=years, index=len(years) - 1, key="b_year")

    b_season = df[df["year"] == b_year].copy()
    max_pa = int(b_season["hit_PA"].max()) if b_season["hit_PA"].notna().any() else 0

    with col_b:
        min_pa = st.slider("최소 타석(PA) 기준", min_value=0, max_value=max_pa if max_pa > 0 else 1,
                            value=min(100, max_pa) if max_pa > 0 else 0, key="b_min_pa")

    batters = b_season[b_season["hit_PA"] >= min_pa].dropna(subset=["hit_AVG"]).copy()
    st.caption(f"조건을 만족하는 타자: {batters['player_name'].nunique()}명")

    st.divider()
    st.subheader("📋 타자 기록 테이블")

    b_sort_options = {
        "OPS 높은순": ("hit_OPS", False), "타율 높은순": ("hit_AVG", False),
        "홈런 많은순": ("hit_HR", False), "이름(가나다순)": ("player_name", True),
    }
    b_sort_choice = st.selectbox("정렬 기준", options=list(b_sort_options.keys()), key="b_sort")
    b_rank_col, b_is_alpha = b_sort_options[b_sort_choice]

    b_table = batters.copy()
    b_table["종합순위"] = b_table["hit_OPS"].rank(ascending=False, method="min").astype("Int64")
    b_table = b_table.sort_values("player_name") if b_is_alpha else b_table.sort_values(b_rank_col, ascending=False)

    b_display_cols = ["종합순위", "player_name", "team", "primary_position", "hit_PA", "hit_AB", "hit_H",
                       "hit_2B", "hit_3B", "hit_HR", "hit_RBI", "hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS"]
    b_display_cols = [c for c in b_display_cols if c in b_table.columns]
    st.dataframe(
        b_table[b_display_cols], use_container_width=True, hide_index=True,
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
    st.subheader("📊 Top 10")

    b_metric_options = {"OPS": "hit_OPS", "타율(AVG)": "hit_AVG", "홈런(HR)": "hit_HR", "출루율(OBP)": "hit_OBP"}
    b_metric_label = st.selectbox("지표 선택", options=list(b_metric_options.keys()), key="b_top_metric")
    b_metric_col = b_metric_options[b_metric_label]

    b_top10 = batters.dropna(subset=[b_metric_col]).sort_values(b_metric_col, ascending=False).head(10)
    if not b_top10.empty:
        b_top10_sorted = b_top10.sort_values(b_metric_col)
        fig_b_top = go.Figure(go.Bar(
            x=b_top10_sorted[b_metric_col], y=b_top10_sorted["player_name"], orientation="h",
            marker_color=COLOR_SEQUENCE[0],
            text=[f"{v:.3f}" if b_metric_col != "hit_HR" else f"{int(v)}" for v in b_top10_sorted[b_metric_col]],
            textposition="outside",
        ))
        fig_b_top.update_xaxes(title=b_metric_label)
        apply_common_layout(fig_b_top, title=f"{b_year}년 {b_metric_label} Top 10", height=420)
        st.plotly_chart(fig_b_top, use_container_width=True, theme=None)
    else:
        st.info("표시할 데이터가 부족합니다.")

# =================================================================
# 투수 탭
# =================================================================
with tab_pitcher:
    render_glossary(["pit_ERA", "pit_WHIP", "pit_K9", "pit_SO"])

    col_a, col_b = st.columns([1, 2])
    with col_a:
        p_year = st.selectbox("시즌 선택", options=years, index=len(years) - 1, key="p_year")

    p_season = df[(df["year"] == p_year) & (df["primary_position"] == "투수")].dropna(subset=["pit_IP"]).copy()
    max_ip = float(p_season["pit_IP"].max()) if not p_season.empty else 0.0

    with col_b:
        min_ip = st.slider("최소 이닝(IP) 기준", min_value=0.0, max_value=max_ip if max_ip > 0 else 1.0,
                            value=min(30.0, max_ip) if max_ip > 0 else 0.0, key="p_min_ip")

    pitchers = p_season[p_season["pit_IP"] >= min_ip].copy()
    st.caption(f"조건을 만족하는 투수: {pitchers['player_name'].nunique()}명")

    st.divider()
    st.subheader("📋 투수 기록 테이블")

    p_sort_options = {
        "ERA 낮은순": ("pit_ERA", False, True), "WHIP 낮은순": ("pit_WHIP", False, True),
        "탈삼진 많은순": ("pit_SO", False, False), "승수 많은순": ("pit_W", False, False),
        "이름(가나다순)": ("player_name", True, True),
    }
    p_sort_choice = st.selectbox("정렬 기준", options=list(p_sort_options.keys()), key="p_sort")
    p_rank_col, p_is_alpha, p_ascending = p_sort_options[p_sort_choice]

    p_table = pitchers.copy()
    p_table["종합순위"] = p_table["pit_ERA"].rank(ascending=True, method="min").astype("Int64")
    p_table = p_table.sort_values("player_name") if p_is_alpha else p_table.sort_values(p_rank_col, ascending=p_ascending)

    p_display_cols = ["종합순위", "player_name", "team", "pit_IP", "pit_W", "pit_L", "pit_SV", "pit_HLD",
                       "pit_ERA", "pit_WHIP", "pit_SO", "pit_BB", "pit_H", "pit_HR"]
    p_display_cols = [c for c in p_display_cols if c in p_table.columns]
    st.dataframe(
        p_table[p_display_cols], use_container_width=True, hide_index=True,
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
    st.subheader("📊 Top 10")

    p_metric_options = {"ERA(낮은순)": ("pit_ERA", True), "WHIP(낮은순)": ("pit_WHIP", True),
                         "탈삼진(SO)": ("pit_SO", False), "탈삼진율(K9)": ("pit_K9", False)}
    p_metric_label = st.selectbox("지표 선택", options=list(p_metric_options.keys()), key="p_top_metric")
    p_metric_col, p_lower_better = p_metric_options[p_metric_label]

    p_top10 = pitchers.dropna(subset=[p_metric_col]).sort_values(p_metric_col, ascending=p_lower_better).head(10)
    if not p_top10.empty:
        p_top10_sorted = p_top10.sort_values(p_metric_col, ascending=not p_lower_better)
        fig_p_top = go.Figure(go.Bar(
            x=p_top10_sorted[p_metric_col], y=p_top10_sorted["player_name"], orientation="h",
            marker_color=COLOR_SEQUENCE[2],
            text=[f"{v:.2f}" if p_metric_col in ("pit_ERA", "pit_WHIP", "pit_K9") else f"{int(v)}" for v in p_top10_sorted[p_metric_col]],
            textposition="outside",
        ))
        fig_p_top.update_xaxes(title=p_metric_label)
        apply_common_layout(fig_p_top, title=f"{p_year}년 {p_metric_label} Top 10", height=420)
        st.plotly_chart(fig_p_top, use_container_width=True, theme=None)
    else:
        st.info("표시할 데이터가 부족합니다.")
