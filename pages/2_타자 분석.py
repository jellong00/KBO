"""
pages/2_Batter_Rank.py
------------------------
타자 분석: 규정타석 필터, 순위가 매겨진 테이블, wOBA 랭킹 바차트,
주루 4분면 분석, 포지션별 수비율 분포(Box Plot)

주: load_data()가 이미 선수-시즌 단위로 포지션 중복 행을 병합해서 반환하므로
    (예: 좌익수/우익수를 겸한 선수는 def_POS가 '좌익수/우익수' 한 줄로 표기됨)
    이 페이지에서 별도의 중복 제거 로직은 필요 없다.
"""

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.data_loader import load_data, get_years, load_position_level_data
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import render_glossary

st.set_page_config(page_title="타자 분석", page_icon="🏏", layout="wide")

df = load_data()
years = get_years(df)

st.title("🏏 타자 분석")
render_glossary(["hit_AVG", "hit_OBP_est", "hit_SLG", "hit_OPS_est", "hit_wOBA_est", "def_FPCT", "run_SBA", "run_SB_pct", "run_OOB"])

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

st.caption(f"조건을 만족하는 타자: {batters['player_name'].nunique()}명 (같은 선수가 여러 포지션을 겸했다면 한 줄로 합쳐서 표기)")

st.divider()

# ---------------------------------------------------------------
# 순위 테이블
# ---------------------------------------------------------------
st.subheader("📋 타자 기록 테이블 (순위)")

rank_options = {
    "OPS(추정) 높은순": ("hit_OPS_est", False),
    "타율 높은순": ("hit_AVG", False),
    "홈런 많은순": ("hit_HR", False),
    "wOBA(추정) 높은순": ("hit_wOBA_est", False),
    "이름(가나다순)": ("player_name", True),
}
sort_choice = st.selectbox("정렬 기준", options=list(rank_options.keys()))
rank_col, is_alpha = rank_options[sort_choice]

table_df = batters.copy()
# '종합순위'는 정렬 기준과 무관하게 항상 OPS(추정) 기준으로 매겨서, 이름순 정렬을 택해도
# 성적 순위를 함께 참고할 수 있도록 함.
table_df["종합순위"] = table_df["hit_OPS_est"].rank(ascending=False, method="min").astype("Int64")

if is_alpha:
    table_df = table_df.sort_values("player_name", ascending=True)
else:
    table_df = table_df.sort_values(rank_col, ascending=False)

display_cols = [
    "종합순위", "player_name", "team", "def_POS", "hit_PA", "hit_AB", "hit_H",
    "hit_2B", "hit_3B", "hit_HR", "hit_RBI", "hit_AVG",
    "hit_OBP_est", "hit_SLG", "hit_OPS_est", "hit_wOBA_est",
]
display_cols = [c for c in display_cols if c in table_df.columns]

st.dataframe(
    table_df[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "종합순위": st.column_config.NumberColumn("종합순위(OPS 기준)"),
        "player_name": st.column_config.TextColumn("선수명"),
        "team": st.column_config.TextColumn("구단"),
        "def_POS": st.column_config.TextColumn("포지션"),
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
# 세이버메트릭스 랭킹 바차트 (wOBA 상위 15명, OPS는 막대 끝 라벨로 함께 표기)
# 기존 버블차트는 점이 겹쳐 가독성이 떨어져 랭킹 바차트로 교체.
# ---------------------------------------------------------------
st.subheader("💠 세이버메트릭스 랭킹 (wOBA 상위 15명)")

top_woba = batters.dropna(subset=["hit_wOBA_est", "hit_OPS_est"]).sort_values("hit_wOBA_est", ascending=False).head(15)

if not top_woba.empty:
    top_woba_sorted = top_woba.sort_values("hit_wOBA_est")  # 가로 막대는 아래->위로 그려지므로 오름차순 정렬
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=top_woba_sorted["hit_wOBA_est"],
        y=top_woba_sorted["player_name"],
        orientation="h",
        marker_color=COLOR_SEQUENCE[0],
        text=[f"wOBA {w:.3f} · OPS {o:.3f}" for w, o in zip(top_woba_sorted["hit_wOBA_est"], top_woba_sorted["hit_OPS_est"])],
        textposition="outside",
        name="wOBA(추정)",
    ))
    fig_bar.update_xaxes(title="wOBA(추정)")
    fig_bar.update_layout(margin=dict(r=160))  # 막대 끝 텍스트 라벨 공간 확보
    apply_common_layout(fig_bar, height=520)
    st.plotly_chart(fig_bar, use_container_width=True)
    st.caption("막대 끝 라벨에 wOBA(추정)와 OPS(추정)를 함께 표기했습니다.")
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
# 포지션별 수비율 분포 (Box Plot)
# 기존 Violin Plot은 겹치는 밀도 곡선 때문에 가독성이 떨어져 Box Plot으로 교체.
# 포지션별 세분화가 필요하므로 포지션 단위 원본(load_position_level_data)을 사용.
# ---------------------------------------------------------------
st.subheader("🧤 포지션별 수비율(FPCT) 분포")

position_df = load_position_level_data()
def_season_df = position_df[position_df["year"] == selected_year]
def_df = def_season_df.dropna(subset=["def_FPCT", "def_POS"])
def_df = def_df[(def_df["def_POS"] != "") & (def_df["def_POS"] != "투수")]

if not def_df.empty:
    # 중앙값이 높은 포지션 순으로 정렬해 비교가 쉽도록 함
    order = def_df.groupby("def_POS")["def_FPCT"].median().sort_values(ascending=False).index.tolist()
    fig_box = px.box(
        def_df,
        x="def_POS",
        y="def_FPCT",
        color="def_POS",
        category_orders={"def_POS": order},
        points="outliers",
        labels={"def_POS": "포지션", "def_FPCT": "수비율"},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig_box.update_layout(showlegend=False)
    apply_common_layout(fig_box, height=480)
    st.plotly_chart(fig_box, use_container_width=True)
else:
    st.info("수비율 데이터가 부족합니다.")
