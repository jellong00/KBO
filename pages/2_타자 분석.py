"""
pages/2_Batter_Rank.py
------------------------
타자 분석: 규정타석 필터, 순위가 매겨진 테이블,
세이버메트릭스 히트맵, 클러치 히팅 랭킹, 대타 스페셜리스트 랭킹,
도루 성공/실패 스택바, 포지션별 평균 수비율 랭킹.

[2024 데이터 업데이트 반영]
- 출루율/장타율/OPS는 이제 대부분 실제 제공값을 사용 (data_loader.py에서 처리)
- 득점권 타율(hit_RISP), 대타 타율(hit_PH_BA) 등 신규 변수를 활용한 분석 추가
- 기존 버블차트/4분면 산점도/바이올린 플롯은 모두 "한눈에 들어오는" 차트(히트맵/막대)로 교체

주: load_data()가 이미 선수-시즌 단위로 포지션 중복 행을 병합해서 반환하므로
    (예: 좌익수/우익수를 겸한 선수는 def_POS가 '좌익수/우익수' 한 줄로 표기됨)
    이 페이지에서 별도의 중복 제거 로직은 필요 없다.
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from utils.data_loader import load_data, get_years, load_position_level_data
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import render_glossary

st.set_page_config(page_title="타자 분석", page_icon="🏏", layout="wide")

df = load_data()
years = get_years(df)

st.title("🏏 타자 분석")
render_glossary([
    "hit_AVG", "hit_OBP_est", "hit_SLG", "hit_OPS_est", "hit_wOBA_est",
    "hit_RISP", "hit_PH_BA", "def_FPCT", "run_SBA", "run_SB_pct", "run_OOB",
])

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
    "OPS 높은순": ("hit_OPS_est", False),
    "타율 높은순": ("hit_AVG", False),
    "홈런 많은순": ("hit_HR", False),
    "wOBA 높은순": ("hit_wOBA_est", False),
    "득점권타율 높은순": ("hit_RISP", False),
    "이름(가나다순)": ("player_name", True),
}
sort_choice = st.selectbox("정렬 기준", options=list(rank_options.keys()))
rank_col, is_alpha = rank_options[sort_choice]

table_df = batters.copy()
# '종합순위'는 정렬 기준과 무관하게 항상 OPS 기준으로 매겨서, 다른 기준으로 정렬해도
# 성적 순위를 함께 참고할 수 있도록 함.
table_df["종합순위"] = table_df["hit_OPS_est"].rank(ascending=False, method="min").astype("Int64")

if is_alpha:
    table_df = table_df.sort_values("player_name", ascending=True)
else:
    table_df = table_df.sort_values(rank_col, ascending=False)

display_cols = [
    "종합순위", "player_name", "team", "def_POS", "hit_PA", "hit_AB", "hit_H",
    "hit_2B", "hit_3B", "hit_HR", "hit_RBI", "hit_AVG",
    "hit_OBP_est", "hit_SLG", "hit_OPS_est", "hit_RISP", "hit_PH_BA",
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
        "hit_OBP_est": st.column_config.NumberColumn("출루율", format="%.3f"),
        "hit_SLG": st.column_config.NumberColumn("장타율", format="%.3f"),
        "hit_OPS_est": st.column_config.NumberColumn("OPS", format="%.3f"),
        "hit_RISP": st.column_config.NumberColumn("득점권타율", format="%.3f"),
        "hit_PH_BA": st.column_config.NumberColumn("대타타율", format="%.3f"),
    },
)
st.caption(
    "ℹ️ 2002년 이후 시즌은 실제 제공된 출루율/장타율/OPS를 사용합니다. "
    "2001년 시즌은 실제 볼넷·사구 기록으로 직접 계산했고, wOBA는 표준 선형가중치 근사치입니다."
)

st.divider()

# ---------------------------------------------------------------
# 1. 세이버메트릭스 히트맵 (Top 15, 여러 지표를 한 번에 비교)
#    기존 버블차트는 점이 겹쳐 가독성이 떨어져, 지표별 상대순위를 색으로 보여주는
#    히트맵으로 교체 (실제 수치는 칸 안에 텍스트로 표기 → 한눈에 비교 가능).
# ---------------------------------------------------------------
st.subheader("💠 세이버메트릭스 히트맵 (OPS 상위 15명)")

metric_cols = ["hit_AVG", "hit_OBP_est", "hit_SLG", "hit_OPS_est", "hit_RISP"]
metric_labels = ["타율", "출루율", "장타율", "OPS", "득점권타율"]

heat_src = batters.dropna(subset=["hit_OPS_est"]).sort_values("hit_OPS_est", ascending=False).head(15)

if not heat_src.empty:
    z_raw = heat_src[metric_cols].to_numpy(dtype=float)
    # 결측치는 해당 지표 평균으로 채워 색상 계산에서 제외되지 않게 함 (텍스트는 원본 결측 그대로 표기)
    col_means = np.nanmean(z_raw, axis=0)
    z_filled = np.where(np.isnan(z_raw), col_means, z_raw)
    col_min = z_filled.min(axis=0)
    col_max = z_filled.max(axis=0)
    z_norm = (z_filled - col_min) / (col_max - col_min + 1e-9)

    text_matrix = np.array([[f"{v:.3f}" if not np.isnan(v) else "-" for v in row] for row in z_raw])

    fig_heat = go.Figure(go.Heatmap(
        z=z_norm.T,
        x=heat_src["player_name"],
        y=metric_labels,
        text=text_matrix.T,
        texttemplate="%{text}",
        textfont=dict(color="#111827", size=12),
        colorscale="RdYlGn",
        showscale=False,
        xgap=3, ygap=3,
    ))
    fig_heat.update_xaxes(tickangle=-40)
    apply_common_layout(fig_heat, title="선수(열) × 지표(행) — 초록에 가까울수록 해당 지표 상위권", height=380)
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.info("표시할 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# 2. 클러치 히팅 랭킹 (득점권 타율 - 전체 타율, 다이버징 바 차트)
# ---------------------------------------------------------------
st.subheader("🔥 클러치 히팅 랭킹 (득점권타율 − 전체타율)")

clutch_df = batters.dropna(subset=["hit_RISP", "hit_AVG"]).copy()
clutch_df["clutch_diff"] = clutch_df["hit_RISP"] - clutch_df["hit_AVG"]

if not clutch_df.empty:
    top_pos = clutch_df.sort_values("clutch_diff", ascending=False).head(8)
    top_neg = clutch_df.sort_values("clutch_diff", ascending=True).head(8)
    combo = pd.concat([top_neg, top_pos]).drop_duplicates(subset=["player_name"]).sort_values("clutch_diff")

    colors = ["#EF4444" if v < 0 else "#10B981" for v in combo["clutch_diff"]]
    fig_clutch = go.Figure(go.Bar(
        x=combo["clutch_diff"],
        y=combo["player_name"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.3f}" for v in combo["clutch_diff"]],
        textposition="outside",
    ))
    fig_clutch.add_vline(x=0, line_color="#94A3B8")
    fig_clutch.update_xaxes(title="득점권타율 − 전체타율")
    apply_common_layout(fig_clutch, height=480)
    st.plotly_chart(fig_clutch, use_container_width=True)
    st.caption("초록(+)은 득점권에서 평소보다 더 잘 치는 '클러치' 유형, 빨강(-)은 득점권에서 오히려 약해지는 유형입니다.")
else:
    st.info("득점권 타율 데이터가 부족합니다. (2002년 이후 시즌에서 제공)")

st.divider()

# ---------------------------------------------------------------
# 3. 대타 스페셜리스트 랭킹 (대타 타율 Top 10)
# ---------------------------------------------------------------
st.subheader("🎭 대타 스페셜리스트 랭킹 (대타 타율 Top 10)")

ph_df = season_df.dropna(subset=["hit_PH_BA"]).sort_values("hit_PH_BA", ascending=False).head(10)
if not ph_df.empty:
    ph_sorted = ph_df.sort_values("hit_PH_BA")
    fig_ph = go.Figure(go.Bar(
        x=ph_sorted["hit_PH_BA"],
        y=ph_sorted["player_name"],
        orientation="h",
        marker_color=COLOR_SEQUENCE[4],
        text=[f"{v:.3f}" for v in ph_sorted["hit_PH_BA"]],
        textposition="outside",
    ))
    fig_ph.update_xaxes(title="대타 타율")
    apply_common_layout(fig_ph, height=420)
    st.plotly_chart(fig_ph, use_container_width=True)
    st.caption("⚠️ 대타 타석 수 자체가 적은 선수가 많아 표본이 작을 수 있습니다 (참고용 지표).")
else:
    st.info("대타 타율 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# 4. 도루 성공/실패 스택 바 차트 (Top 12 도루 시도자)
#    기존 4분면 산점도 대신, 성공(SB)과 실패(CS)를 쌓아 올린 막대로 표현해
#    누가 얼마나 많이 뛰었고 그 중 몇 번 성공/실패했는지 한눈에 보이게 함.
# ---------------------------------------------------------------
st.subheader("🏃 도루 시도 Top 12 (성공/실패 스택 바 차트)")

run_df = season_df.dropna(subset=["run_SBA"])
run_df = run_df[run_df["run_SBA"] > 0].sort_values("run_SBA", ascending=False).head(12)

if not run_df.empty:
    run_sorted = run_df.sort_values("run_SBA")
    fig_run = go.Figure()
    fig_run.add_trace(go.Bar(
        x=run_sorted["run_SB"], y=run_sorted["player_name"], orientation="h",
        name="도루 성공(SB)", marker_color="#10B981",
    ))
    fig_run.add_trace(go.Bar(
        x=run_sorted["run_CS"], y=run_sorted["player_name"], orientation="h",
        name="도루 실패(CS)", marker_color="#EF4444",
    ))
    fig_run.update_layout(barmode="stack")
    fig_run.update_xaxes(title="도루 시도 횟수 (성공+실패)")
    apply_common_layout(fig_run, height=480)
    st.plotly_chart(fig_run, use_container_width=True)
    st.caption("막대 전체 길이가 도루 시도 횟수이며, 초록(성공)과 빨강(실패)의 비율로 도루 성공률을 한눈에 볼 수 있습니다.")
else:
    st.info("도루 시도 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# 5. 포지션별 평균 수비율 랭킹 (가로 막대)
#    기존 Box/Violin Plot 대신 포지션별 평균값을 단순 막대로 비교.
#    포지션별 세분화가 필요하므로 포지션 단위 원본(load_position_level_data)을 사용.
# ---------------------------------------------------------------
st.subheader("🧤 포지션별 평균 수비율(FPCT) 랭킹")

position_df = load_position_level_data()
def_season_df = position_df[position_df["year"] == selected_year]
def_df = def_season_df.dropna(subset=["def_FPCT", "def_POS"])
def_df = def_df[(def_df["def_POS"] != "") & (def_df["def_POS"] != "투수")]

if not def_df.empty:
    pos_avg = def_df.groupby("def_POS")["def_FPCT"].mean().sort_values()
    fig_pos = go.Figure(go.Bar(
        x=pos_avg.values,
        y=pos_avg.index,
        orientation="h",
        marker_color=COLOR_SEQUENCE[2],
        text=[f"{v:.3f}" for v in pos_avg.values],
        textposition="outside",
    ))
    fig_pos.update_xaxes(title="평균 수비율(FPCT)", range=[pos_avg.min() * 0.97, 1.01])
    apply_common_layout(fig_pos, height=420)
    st.plotly_chart(fig_pos, use_container_width=True)
else:
    st.info("수비율 데이터가 부족합니다.")
