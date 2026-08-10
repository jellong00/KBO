"""
pages/1_기초통계.py
---------------------
교육용 핵심 페이지: 지표 하나를 골라 평균/중앙값/표준편차/분포/이상치를
동시에 보여주고, "평균이 항상 대표값으로 적절한가?"를 체감하게 함.
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from utils.data_loader import load_data, get_years
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import render_glossary, STAT_GLOSSARY

st.set_page_config(page_title="기초통계 탐색", page_icon="📊", layout="wide")

df = load_data()
years = get_years(df)

st.title("📊 기초통계 탐색")
st.caption("지표를 하나 골라서 평균·중앙값·표준편차·분포 모양을 직접 확인해보세요.")

# ---------------------------------------------------------------
# 지표 선택
# ---------------------------------------------------------------
metric_options = {
    "타율 (hit_AVG)": "hit_AVG",
    "홈런 (hit_HR)": "hit_HR",
    "출루율 (hit_OBP)": "hit_OBP",
    "장타율 (hit_SLG)": "hit_SLG",
    "OPS (hit_OPS)": "hit_OPS",
    "타점 (hit_RBI)": "hit_RBI",
    "평균자책점 ERA (pit_ERA)": "pit_ERA",
    "WHIP (pit_WHIP)": "pit_WHIP",
    "탈삼진 (pit_SO)": "pit_SO",
    "이닝 (pit_IP)": "pit_IP",
    "수비율 (def_FPCT)": "def_FPCT",
    "도루성공률 (run_SB_pct)": "run_SB_pct",
}

col_a, col_b = st.columns([1.3, 1])
with col_a:
    metric_label = st.selectbox("탐색할 지표 선택", options=list(metric_options.keys()))
    metric_col = metric_options[metric_label]
with col_b:
    selected_year = st.selectbox("연도 선택 (전체 기간 vs 특정 시즌)", options=["전체 기간"] + years)

render_glossary([metric_col])

if selected_year == "전체 기간":
    data = df.dropna(subset=[metric_col])
else:
    data = df[df["year"] == selected_year].dropna(subset=[metric_col])

# 표본 크기가 너무 작은 지표(투수/타자 전용)를 위해 최소 관측치 필터링 안내
if data.empty:
    st.warning("해당 조건에서 데이터가 없습니다.")
    st.stop()

series = data[metric_col]

st.divider()

# ---------------------------------------------------------------
# 중심경향치 + 산포도
# ---------------------------------------------------------------
st.subheader("1️⃣ 중심경향치 & 산포도")

mean_v = series.mean()
median_v = series.median()
std_v = series.std()
q1, q3 = series.quantile(0.25), series.quantile(0.75)
iqr = q3 - q1
skew_v = series.skew()

m1, m2, m3, m4 = st.columns(4)
m1.metric("평균(Mean)", f"{mean_v:.3f}")
m2.metric("중앙값(Median)", f"{median_v:.3f}", delta=f"{mean_v - median_v:+.3f} (평균-중앙값)")
m3.metric("표준편차(SD)", f"{std_v:.3f}")
m4.metric("사분위범위(IQR)", f"{iqr:.3f}", help=f"Q1={q1:.3f}, Q3={q3:.3f}")

if abs(skew_v) > 1:
    direction = "오른쪽(고값 방향)" if skew_v > 0 else "왼쪽(저값 방향)"
    st.info(
        f"📌 **이 지표는 분포가 많이 치우쳐 있어요 (왜도={skew_v:.2f}, {direction}으로 긴 꼬리).** "
        "이런 경우 평균은 극단값에 민감하게 끌려가므로, '대표값'으로는 **중앙값**이 더 안정적일 수 있습니다."
    )
else:
    st.success(f"📌 이 지표는 비교적 대칭적인 분포입니다 (왜도={skew_v:.2f}). 평균과 중앙값이 대표값으로 비슷하게 적절합니다.")

st.divider()

# ---------------------------------------------------------------
# 히스토그램
# ---------------------------------------------------------------
st.subheader("2️⃣ 히스토그램 (분포 모양)")

fig_hist = go.Figure()
fig_hist.add_trace(go.Histogram(x=series, nbinsx=40, marker_color=COLOR_SEQUENCE[0], opacity=0.85))
fig_hist.add_vline(x=mean_v, line_color=COLOR_SEQUENCE[3], line_width=2,
                    annotation_text="평균", annotation_position="top")
fig_hist.add_vline(x=median_v, line_color=COLOR_SEQUENCE[2], line_width=2, line_dash="dash",
                    annotation_text="중앙값", annotation_position="bottom")
fig_hist.update_xaxes(title=metric_label)
fig_hist.update_yaxes(title="빈도(선수-시즌 수)")
apply_common_layout(fig_hist, height=420)
st.plotly_chart(fig_hist, use_container_width=True)
st.caption("빨간 실선=평균, 초록 점선=중앙값. 두 선이 멀리 떨어져 있을수록 분포가 비대칭적이라는 뜻입니다.")

st.divider()

# ---------------------------------------------------------------
# 연도별 박스플롯 (전체 기간 선택 시에만 의미 있음)
# ---------------------------------------------------------------
st.subheader("3️⃣ 연도별 분포 변화 (박스플롯)")

box_data = df.dropna(subset=[metric_col])
fig_box = go.Figure()
fig_box.add_trace(go.Box(
    x=box_data["year"], y=box_data[metric_col],
    marker_color=COLOR_SEQUENCE[1], boxpoints=False,
))
fig_box.update_xaxes(title="연도", dtick=2)
fig_box.update_yaxes(title=metric_label)
apply_common_layout(fig_box, height=460)
st.plotly_chart(fig_box, use_container_width=True)
st.caption(
    "박스의 가운데 선은 중앙값, 박스 상/하단은 각각 Q3/Q1(사분위수), 위아래 수염은 이상치를 제외한 범위입니다. "
    "박스의 위치나 크기가 연도마다 달라진다면 '시대에 따라 이 지표의 기준 자체가 변했다'는 뜻입니다."
)

st.divider()

# ---------------------------------------------------------------
# 이상치(아웃라이어) 예시
# ---------------------------------------------------------------
st.subheader("4️⃣ 이상치(아웃라이어) 살펴보기")
st.caption("IQR 기준(Q1 - 1.5×IQR ~ Q3 + 1.5×IQR)을 벗어나는 값들입니다. 극단적인 시즌을 보낸 선수들을 확인해보세요.")

lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr
outliers = data[(data[metric_col] < lower_bound) | (data[metric_col] > upper_bound)]
outliers = outliers.sort_values(metric_col, ascending=False)

st.write(f"전체 {len(data):,}건 중 이상치 **{len(outliers):,}건** ({len(outliers)/len(data)*100:.1f}%)")

if not outliers.empty:
    show_cols = ["player_name", "year", "team", "primary_position", metric_col]
    st.dataframe(
        outliers[show_cols].head(20),
        use_container_width=True, hide_index=True,
        column_config={metric_col: st.column_config.NumberColumn(metric_label, format="%.3f")},
    )
else:
    st.info("이 조건에서는 이상치가 없습니다.")
