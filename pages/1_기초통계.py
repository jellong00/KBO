"""
pages/1_기초통계.py
---------------------
과제 연계형 기초통계 페이지 (1/2): 기술통계표 + 분포
- 분석대상: 타자, 최소 타석(PA) 기준을 학생이 직접 조정하며 표본 제한의 효과를 체감
- AVG/OBP/SLG/OPS/HR 기술통계표 (N, mean, sd, p25, p50, p75, IQR, min, max)
- 단순평균 vs PA 가중평균 비교
- 히스토그램(평균/중앙값선 포함) + 박스플롯(IQR·이상치)
- PA 기준 민감도 비교
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.data_loader import load_data, get_years
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import render_glossary

st.set_page_config(page_title="기초통계 1: 기술통계와 분포", page_icon="📊", layout="wide")

df = load_data()
years = get_years(df)

st.title("📊 기초통계 (1/2): 기술통계표와 분포")
st.caption("분석 대상은 **타자**로 한정합니다. (투수 지표는 다루지 않습니다)")
render_glossary(["hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS"])

# ---------------------------------------------------------------
# 0. 분석 표본 설정
# ---------------------------------------------------------------
st.subheader("0️⃣ 분석 표본 설정")

col_a, col_b = st.columns([1, 1.5])
with col_a:
    year_choice = st.selectbox("연도 선택", options=["전체 기간"] + years, index=0)
with col_b:
    min_pa = st.slider(
        "최소 타석(PA) 기준", min_value=0, max_value=300, value=100, step=10,
        help="이 기준은 분석자가 임의로 설정하는 표본 제한 기준입니다. KBO 공식 '규정타석'과는 다릅니다.",
    )

st.caption(
    f"⚠️ PA≥{min_pa}은 **분석자가 설정한 표본 제한 기준**입니다. "
    "KBO의 공식 규정타석(대략 '팀 경기수 × 3.1')과는 다른 개념이니 혼동하지 마세요."
)

base = df[df["hit_PA"].notna()].copy()
if year_choice != "전체 기간":
    base = base[base["year"] == year_choice]

all_batters = base.copy()
filtered_batters = base[base["hit_PA"] >= min_pa].copy()

st.caption(
    f"전체 타자(필터 없음): **{len(all_batters):,}개 선수-시즌 관측치** · "
    f"필터 적용 후(PA≥{min_pa}): **{len(filtered_batters):,}개 선수-시즌 관측치**"
)

st.divider()

# ---------------------------------------------------------------
# 1. 표본 제한의 효과
# ---------------------------------------------------------------
st.subheader("1️⃣ 왜 표본 크기 기준이 필요한가?")
st.caption("타석 수가 매우 적으면, 표본이 작아 우연의 영향을 크게 받는 극단값이 나타날 수 있습니다.")

extreme = (
    all_batters[all_batters["hit_PA"] < 20]
    .dropna(subset=["hit_AVG"])
    .sort_values("hit_AVG", ascending=False)
    .head(8)
)
if not extreme.empty:
    st.write("**타석 20타석 미만 사례 (표본이 작아 우연의 영향이 큰 경우)**")
    st.dataframe(
        extreme[["player_name", "year", "team", "hit_PA", "hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS", "hit_HR"]],
        use_container_width=True, hide_index=True,
        column_config={
            "player_name": st.column_config.TextColumn("선수명"),
            "hit_PA": st.column_config.NumberColumn("타석"),
            "hit_AVG": st.column_config.NumberColumn("타율", format="%.3f"),
            "hit_OBP": st.column_config.NumberColumn("출루율", format="%.3f"),
            "hit_SLG": st.column_config.NumberColumn("장타율", format="%.3f"),
            "hit_OPS": st.column_config.NumberColumn("OPS", format="%.3f"),
            "hit_HR": st.column_config.NumberColumn("홈런"),
        },
    )
    st.warning(
        "타석이 몇 안 되는 상태에서 어쩌다 안타 몇 개를 몰아치면, 타율·OPS 같은 비율 지표가 표본이 커졌을 때와는 "
        "전혀 다른 값으로 나타날 수 있습니다. 표본 제한 기준은 이런 '우연에 의한 극단값'을 걸러내기 위한 장치입니다."
    )

comp_col1, comp_col2 = st.columns(2)
with comp_col1:
    st.markdown("**A. 전체 타자 (필터 없음)**")
    st.metric("표본 크기", f"{len(all_batters):,}개 관측치")
    max_ops_all = all_batters["hit_OPS"].max()
    st.metric("OPS 최댓값", f"{max_ops_all:.3f}" if pd.notna(max_ops_all) else "N/A")
with comp_col2:
    st.markdown(f"**B. PA ≥ {min_pa} 필터 적용**")
    st.metric("표본 크기", f"{len(filtered_batters):,}개 관측치")
    max_ops_filt = filtered_batters["hit_OPS"].max()
    st.metric("OPS 최댓값", f"{max_ops_filt:.3f}" if pd.notna(max_ops_filt) else "N/A")

st.divider()

# ---------------------------------------------------------------
# 2. 기술통계표
# ---------------------------------------------------------------
st.subheader("2️⃣ 기술통계표")
st.caption(f"표본: PA ≥ {min_pa} 타자, {year_choice}. **N은 '선수 수'가 아니라 '선수-시즌 관측치 수'입니다** (같은 선수가 여러 시즌 뛰면 각 시즌이 별도로 집계됩니다).")

metrics = {"hit_AVG": "타율(AVG)", "hit_OBP": "출루율(OBP)", "hit_SLG": "장타율(SLG)",
           "hit_OPS": "OPS", "hit_HR": "홈런(HR)"}


def skew_interpretation(sk):
    if sk > 1:
        return "오른쪽 꼬리(양의 왜도) — 소수의 매우 높은 값이 평균을 끌어올림"
    elif sk < -1:
        return "왼쪽 꼬리(음의 왜도) — 소수의 매우 낮은 값이 평균을 끌어내림"
    else:
        return "비교적 대칭적"


desc_rows = []
for col, label in metrics.items():
    s = filtered_batters[col].dropna()
    if s.empty:
        continue
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    desc_rows.append({
        "지표": label, "N": len(s), "평균(mean)": s.mean(), "표준편차(sd)": s.std(),
        "최솟값(min)": s.min(), "p25": q1, "중앙값(p50)": s.median(), "p75": q3,
        "IQR(p75-p25)": q3 - q1, "최댓값(max)": s.max(), "왜도(skewness)": s.skew(),
        "분포 해석": skew_interpretation(s.skew()),
    })
desc_df = pd.DataFrame(desc_rows)

num_cols = ["평균(mean)", "표준편차(sd)", "최솟값(min)", "p25", "중앙값(p50)", "p75",
            "IQR(p75-p25)", "최댓값(max)", "왜도(skewness)"]
st.dataframe(
    desc_df, use_container_width=True, hide_index=True,
    column_config={c: st.column_config.NumberColumn(c, format="%.3f") for c in num_cols},
)

st.caption(
    "💡 각 지표의 **평균과 중앙값을 그 지표 내부에서** 비교해보세요 (단위가 다른 지표끼리 차이값을 직접 비교하는 것은 "
    "적절하지 않습니다 — 예: 홈런 개수와 타율은 스케일 자체가 다릅니다). "
    "지표별 N이 다르게 나온다면, 그 지표에 결측치(예: 시즌 중 기록되지 않은 값)가 있었기 때문일 수 있습니다."
)

st.divider()

# ---------------------------------------------------------------
# 3. 단순평균 vs PA 가중평균
# ---------------------------------------------------------------
st.subheader("3️⃣ 단순평균 vs 타석(PA) 가중평균")
st.caption(
    "'선수별 평균'을 그냥 평균 내면(단순평균), 타석이 10개인 선수와 500개인 선수가 똑같은 비중을 갖습니다. "
    "타석 수로 가중치를 주면(가중평균), 실제로 리그에 더 크게 기여한 선수의 비중이 커집니다."
)

weight_rows = []
for col, label in metrics.items():
    if col == "hit_HR":
        continue  # 카운트 지표는 가중평균 개념이 비율 지표만큼 직관적이지 않아 제외
    sub = filtered_batters.dropna(subset=[col, "hit_PA"])
    if sub.empty:
        continue
    simple_mean = sub[col].mean()
    weighted_mean = np.average(sub[col], weights=sub["hit_PA"])
    weight_rows.append({
        "지표": label, "단순평균": simple_mean, "PA 가중평균": weighted_mean,
        "차이(가중-단순)": weighted_mean - simple_mean,
    })

weight_df = pd.DataFrame(weight_rows)
st.dataframe(
    weight_df, use_container_width=True, hide_index=True,
    column_config={c: st.column_config.NumberColumn(c, format="%.4f") for c in ["단순평균", "PA 가중평균", "차이(가중-단순)"]},
)
st.caption("💡 두 평균이 크게 다르다면, 타석이 많은(주전급) 선수와 적은(백업/대타) 선수의 성적 경향이 서로 다르다는 뜻일 수 있습니다.")

st.divider()

# ---------------------------------------------------------------
# 4. 히스토그램 (평균/중앙값선 포함)
# ---------------------------------------------------------------
st.subheader("4️⃣ 히스토그램으로 분포 비교")

hist_metrics = ["hit_OPS", "hit_HR", "hit_AVG"]
hist_labels = ["OPS", "홈런(HR)", "타율(AVG)"]

fig = make_subplots(rows=1, cols=3, subplot_titles=hist_labels)
for i, (col, label) in enumerate(zip(hist_metrics, hist_labels)):
    s = filtered_batters[col].dropna()
    fig.add_trace(
        go.Histogram(x=s, nbinsx=30, marker_color=COLOR_SEQUENCE[i], showlegend=False),
        row=1, col=i + 1,
    )
    fig.add_vline(x=s.mean(), line_color="#111827", line_width=2, row=1, col=i + 1)
    fig.add_vline(x=s.median(), line_color="#111827", line_width=2, line_dash="dash", row=1, col=i + 1)
apply_common_layout(fig, height=380)
fig.update_annotations(font=dict(color="#111827", size=13))
st.plotly_chart(fig, use_container_width=True, theme=None)
st.caption("실선=평균, 점선=중앙값. 두 선이 멀리 떨어져 있을수록 그 지표 자체의 분포가 비대칭적이라는 뜻입니다.")

st.markdown("""
**생각해볼 질문**
- 세 변수 중 어떤 분포가 정규분포(종 모양)에 가장 가까운가요?
- 어떤 변수에서 극단값(긴 꼬리)이 가장 많이 관찰되나요?
- 평균이 그 변수의 '대표값'으로 적절한가요, 아니면 중앙값이 더 나을까요?
""")

st.divider()

# ---------------------------------------------------------------
# 5. 박스플롯 (IQR·이상치)
# ---------------------------------------------------------------
st.subheader("5️⃣ 박스플롯으로 IQR과 이상치 확인하기")

box_metric_label = st.selectbox("박스플롯으로 볼 지표 선택", options=["OPS", "홈런(HR)"], index=0)
box_col = "hit_OPS" if box_metric_label == "OPS" else "hit_HR"
box_series = filtered_batters[box_col].dropna()

fig_box = go.Figure()
fig_box.add_trace(go.Box(y=box_series, marker_color=COLOR_SEQUENCE[0], boxpoints="outliers", name=box_metric_label))
fig_box.update_yaxes(title=box_metric_label)
apply_common_layout(fig_box, height=440)
st.plotly_chart(fig_box, use_container_width=True, theme=None)
st.caption(
    "박스 상단/하단이 각각 p75/p25(IQR의 경계), 박스 안의 선이 중앙값입니다. "
    "박스 밖의 점들은 'Q1-1.5×IQR ~ Q3+1.5×IQR' 범위를 벗어난 이상치입니다."
)

st.divider()

# ---------------------------------------------------------------
# 6. PA 기준 민감도 비교
# ---------------------------------------------------------------
st.subheader("6️⃣ PA 기준을 바꾸면 통계치가 어떻게 달라지는가?")
st.caption("최소 타석 기준을 0, 50, 100, 200으로 바꿔가며 표본 크기와 기술통계가 어떻게 변하는지 비교해보세요.")

pa_thresholds = [0, 50, 100, 200]
sens_rows = []
for pa_th in pa_thresholds:
    sub = base[base["hit_PA"] >= pa_th]["hit_OPS"].dropna()
    if sub.empty:
        continue
    sens_rows.append({
        "PA 기준": f"≥{pa_th}", "N": len(sub), "평균(OPS)": sub.mean(),
        "표준편차(OPS)": sub.std(), "최댓값(OPS)": sub.max(),
    })
sens_df = pd.DataFrame(sens_rows)
st.dataframe(
    sens_df, use_container_width=True, hide_index=True,
    column_config={c: st.column_config.NumberColumn(c, format="%.3f") for c in ["평균(OPS)", "표준편차(OPS)", "최댓값(OPS)"]},
)
st.markdown("""
**생각해볼 질문**
- PA 기준을 높일수록 N, 평균, 표준편차, 최댓값은 각각 어떻게 변하나요?
- 표준편차와 최댓값이 줄어드는 이유는 무엇일까요?
- 기준을 너무 높게 잡으면 어떤 문제가 생길 수 있을까요? (힌트: 표본 크기 자체가 너무 작아짐)
""")
