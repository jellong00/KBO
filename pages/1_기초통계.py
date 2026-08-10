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
from scipy import stats

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
st.plotly_chart(fig_hist, use_container_width=True, theme=None)
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
st.plotly_chart(fig_box, use_container_width=True, theme=None)
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

st.divider()

# ---------------------------------------------------------------
# 정규분포와의 비교
# ---------------------------------------------------------------
st.subheader("5️⃣ 정규분포와 비교해보기")
st.caption("실제 데이터의 히스토그램 위에, 같은 평균·표준편차를 가진 이론적 정규분포 곡선을 겹쳐서 '정규성'을 육안으로 확인합니다.")

x_range = np.linspace(series.min(), series.max(), 200)
normal_pdf = stats.norm.pdf(x_range, mean_v, std_v)
bin_width = (series.max() - series.min()) / 40
normal_scaled = normal_pdf * len(series) * bin_width

fig_norm = go.Figure()
fig_norm.add_trace(go.Histogram(x=series, nbinsx=40, marker_color=COLOR_SEQUENCE[0], opacity=0.7, name="실제 분포"))
fig_norm.add_trace(go.Scatter(x=x_range, y=normal_scaled, mode="lines", name="이론적 정규분포",
                               line=dict(color=COLOR_SEQUENCE[3], width=3)))
fig_norm.update_xaxes(title=metric_label)
fig_norm.update_yaxes(title="빈도")
apply_common_layout(fig_norm, height=420)
st.plotly_chart(fig_norm, use_container_width=True, theme=None)

# 샤피로-윌크 정규성 검정 (표본이 너무 크면 왜곡되므로 5000개로 표본추출)
test_sample = series.sample(min(len(series), 5000), random_state=42)
shapiro_stat, shapiro_p = stats.shapiro(test_sample)
if shapiro_p < 0.05:
    st.warning(
        f"📌 **Shapiro-Wilk 정규성 검정: W={shapiro_stat:.4f}, p={shapiro_p:.4f} (p<0.05)** → "
        "이 지표는 통계적으로 정규분포를 따른다고 보기 어렵습니다. 평균 기반 검정(t검정 등)을 쓸 때 주의가 필요합니다."
    )
else:
    st.success(
        f"📌 **Shapiro-Wilk 정규성 검정: W={shapiro_stat:.4f}, p={shapiro_p:.4f} (p≥0.05)** → "
        "정규분포 가정을 기각할 근거가 부족합니다. (표본이 클수록 이 검정은 민감해지니 곡선과 히스토그램의 육안 비교도 함께 참고하세요.)"
    )

st.divider()

# ---------------------------------------------------------------
# 표준오차와 신뢰구간
# ---------------------------------------------------------------
st.subheader("6️⃣ 표준오차(SE)와 95% 신뢰구간")
st.caption("'표본평균'이 '모평균'을 얼마나 정확하게 추정하는지를 보여주는 구간입니다. 표본이 클수록 구간이 좁아집니다(추정이 정밀해짐).")

n = len(series)
se = std_v / np.sqrt(n)
t_crit = stats.t.ppf(0.975, df=n - 1)
ci_lower = mean_v - t_crit * se
ci_upper = mean_v + t_crit * se

c1, c2, c3 = st.columns(3)
c1.metric("표본 크기 (n)", f"{n:,}")
c2.metric("표준오차 (SE = SD/√n)", f"{se:.5f}")
c3.metric("95% 신뢰구간", f"[{ci_lower:.4f}, {ci_upper:.4f}]")

fig_ci = go.Figure()
fig_ci.add_trace(go.Scatter(
    x=[ci_lower, ci_upper], y=["평균"] * 2, mode="lines",
    line=dict(color=COLOR_SEQUENCE[0], width=6), showlegend=False,
))
fig_ci.add_trace(go.Scatter(
    x=[mean_v], y=["평균"], mode="markers", marker=dict(color=COLOR_SEQUENCE[3], size=14, symbol="diamond"),
    name="표본평균", showlegend=False,
))
fig_ci.update_xaxes(title=metric_label)
fig_ci.update_yaxes(title="", showticklabels=True)
apply_common_layout(fig_ci, height=200)
st.plotly_chart(fig_ci, use_container_width=True, theme=None)
st.caption(
    "💡 표본 크기(n)를 바꿔서(예: 특정 연도만 선택) 신뢰구간의 폭이 어떻게 달라지는지 비교해보세요. "
    "n이 작을수록 구간이 넓어져 '덜 정밀한 추정'이 됩니다."
)

st.divider()

# ---------------------------------------------------------------
# 두 지표 간 상관관계
# ---------------------------------------------------------------
st.subheader("7️⃣ 두 지표 간 상관관계")
st.caption("산점도와 피어슨 상관계수(r)로 두 지표가 함께 움직이는 정도를 확인합니다. 상관관계≠인과관계라는 점에 유의하세요.")

metric_col2 = st.selectbox(
    "비교할 두 번째 지표 선택",
    options=[k for k in metric_options.keys() if metric_options[k] != metric_col],
    key="metric2",
)
metric_col2_name = metric_options[metric_col2]

corr_data = data.dropna(subset=[metric_col, metric_col2_name])
if len(corr_data) >= 3:
    r, p_val = stats.pearsonr(corr_data[metric_col], corr_data[metric_col2_name])

    fig_scatter = go.Figure()
    fig_scatter.add_trace(go.Scatter(
        x=corr_data[metric_col], y=corr_data[metric_col2_name], mode="markers",
        marker=dict(color=COLOR_SEQUENCE[0], size=6, opacity=0.5),
    ))
    # 회귀선 추가
    slope, intercept = np.polyfit(corr_data[metric_col], corr_data[metric_col2_name], 1)
    x_line = np.array([corr_data[metric_col].min(), corr_data[metric_col].max()])
    fig_scatter.add_trace(go.Scatter(
        x=x_line, y=slope * x_line + intercept, mode="lines",
        line=dict(color=COLOR_SEQUENCE[3], width=3), name="추세선",
    ))
    fig_scatter.update_xaxes(title=metric_label)
    fig_scatter.update_yaxes(title=metric_col2)
    apply_common_layout(fig_scatter, title=f"r = {r:.3f} (p = {p_val:.4f})", height=460)
    st.plotly_chart(fig_scatter, use_container_width=True, theme=None)

    abs_r = abs(r)
    if abs_r < 0.1:
        strength = "거의 없음"
    elif abs_r < 0.3:
        strength = "약함"
    elif abs_r < 0.5:
        strength = "중간"
    elif abs_r < 0.7:
        strength = "강함"
    else:
        strength = "매우 강함"
    direction = "양(+)의" if r > 0 else "음(−)의"
    sig_text = "통계적으로 유의합니다 (p<0.05)" if p_val < 0.05 else "통계적으로 유의하지 않습니다 (p≥0.05)"
    st.info(f"📌 두 지표는 **{direction} 상관관계**를 보이며, 강도는 **{strength}**({abs_r:.2f})입니다. 이 상관은 {sig_text}.")
else:
    st.warning("상관관계를 계산하기에 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# 집단 비교 (두 시대 비교, 독립표본 t검정)
# ---------------------------------------------------------------
st.subheader("8️⃣ 두 시대 비교: 평균 차이가 통계적으로 유의한가?")
st.caption("연도를 기준으로 두 시기로 나눠서, 지표의 평균이 실제로 다른지 독립표본 t검정으로 확인합니다.")

split_year = st.slider(
    "분기점 연도 선택 (이 연도 포함 이전 vs 이후)",
    min_value=int(years[1]), max_value=int(years[-1]), value=int(years[len(years) // 2]),
)

group1 = df[(df["year"] <= split_year)].dropna(subset=[metric_col])[metric_col]
group2 = df[(df["year"] > split_year)].dropna(subset=[metric_col])[metric_col]

if len(group1) >= 2 and len(group2) >= 2:
    t_stat, t_p = stats.ttest_ind(group1, group2, equal_var=False)  # Welch's t-test

    g1, g2, g3, g4 = st.columns(4)
    g1.metric(f"{years[0]}~{split_year} 평균", f"{group1.mean():.3f}", help=f"n={len(group1):,}")
    g2.metric(f"{split_year + 1}~{years[-1]} 평균", f"{group2.mean():.3f}", help=f"n={len(group2):,}")
    g3.metric("t-통계량", f"{t_stat:.3f}")
    g4.metric("p-value", f"{t_p:.4f}")

    fig_group = go.Figure()
    fig_group.add_trace(go.Box(y=group1, name=f"~{split_year}", marker_color=COLOR_SEQUENCE[0], boxpoints=False))
    fig_group.add_trace(go.Box(y=group2, name=f"{split_year + 1}~", marker_color=COLOR_SEQUENCE[1], boxpoints=False))
    fig_group.update_yaxes(title=metric_label)
    apply_common_layout(fig_group, height=420)
    st.plotly_chart(fig_group, use_container_width=True, theme=None)

    if t_p < 0.05:
        st.success(f"📌 p={t_p:.4f} < 0.05 → 두 시기의 평균 차이는 **통계적으로 유의**합니다. 우연으로 보기 어려운 차이입니다.")
    else:
        st.info(f"📌 p={t_p:.4f} ≥ 0.05 → 두 시기의 평균 차이가 통계적으로 유의하다고 보기 어렵습니다 (우연한 차이일 수 있음).")
else:
    st.warning("두 집단 중 하나의 표본 크기가 너무 작아 검정을 수행할 수 없습니다.")

st.divider()

# ---------------------------------------------------------------
# 범주형 변수 도수분포표
# ---------------------------------------------------------------
st.subheader("9️⃣ 범주형 변수 도수분포표")
st.caption("숫자가 아닌 범주형 변수(포지션, 구단 등)는 '도수(빈도)'로 분포를 요약합니다.")

cat_options = {"주포지션 (primary_position)": "primary_position", "구단 (team)": "team"}
cat_label = st.selectbox("범주형 변수 선택", options=list(cat_options.keys()))
cat_col = cat_options[cat_label]

freq = df[cat_col].value_counts().reset_index()
freq.columns = [cat_label, "빈도"]
freq["비율(%)"] = (freq["빈도"] / freq["빈도"].sum() * 100).round(1)
freq["누적비율(%)"] = freq["비율(%)"].cumsum().round(1)

col_table, col_chart = st.columns([1, 1.4])
with col_table:
    st.dataframe(freq, use_container_width=True, hide_index=True)
with col_chart:
    fig_freq = go.Figure(go.Bar(
        x=freq["빈도"], y=freq[cat_label], orientation="h", marker_color=COLOR_SEQUENCE[4],
    ))
    fig_freq.update_yaxes(autorange="reversed")
    fig_freq.update_xaxes(title="빈도(선수-시즌 수)")
    apply_common_layout(fig_freq, height=max(320, 24 * len(freq)))
    st.plotly_chart(fig_freq, use_container_width=True, theme=None)
