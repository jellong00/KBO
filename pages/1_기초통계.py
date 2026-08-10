"""
pages/1_기초통계.py
---------------------
과제 연계형 기초통계 페이지 (1/2): 기술통계표 + 분포
- 분석대상: 타자, 최소 타석(PA) 기준을 학생이 직접 조정하며 표본 제한의 효과를 체감
- AVG/OBP/SLG/OPS/HR 기술통계표 (N, mean, sd, min, p50, max)
- OPS/HR/AVG 히스토그램 비교
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
        help="타석 수가 너무 적으면 AVG=1.000, OPS=4.000 같은 비현실적인 값이 나올 수 있습니다.",
    )

base = df[df["hit_PA"].notna()].copy()
if year_choice != "전체 기간":
    base = base[base["year"] == year_choice]

all_batters = base.copy()
filtered_batters = base[base["hit_PA"] >= min_pa].copy()

st.caption(
    f"전체 타자(필터 없음): **{len(all_batters):,}명-시즌** · "
    f"필터 적용 후(PA≥{min_pa}): **{len(filtered_batters):,}명-시즌**"
)

st.divider()

# ---------------------------------------------------------------
# 1. 표본 제한의 효과 (극단값 시연)
# ---------------------------------------------------------------
st.subheader("1️⃣ 왜 최소 타석 기준이 필요한가?")
st.caption("타석 수가 매우 적은 선수는 어쩌다 한두 번 잘 치면 타율/OPS가 비현실적으로 치솟을 수 있습니다.")

extreme = (
    all_batters[all_batters["hit_PA"] < 20]
    .dropna(subset=["hit_AVG"])
    .sort_values("hit_AVG", ascending=False)
    .head(8)
)
if not extreme.empty:
    st.write("**타석 20타석 미만인데 극단적인 성적을 보이는 사례**")
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
    st.warning("이래서 '규정 타석'처럼 최소 표본 크기 기준이 필요합니다. 표본이 너무 작으면 우연에 의한 극단값이 섞여 들어갑니다.")

comp_col1, comp_col2 = st.columns(2)
with comp_col1:
    st.markdown("**A. 전체 타자 (필터 없음)**")
    st.metric("표본 크기", f"{len(all_batters):,}명-시즌")
    max_ops_all = all_batters["hit_OPS"].max()
    st.metric("OPS 최댓값", f"{max_ops_all:.3f}" if pd.notna(max_ops_all) else "N/A")
with comp_col2:
    st.markdown(f"**B. PA ≥ {min_pa} 필터 적용**")
    st.metric("표본 크기", f"{len(filtered_batters):,}명-시즌")
    max_ops_filt = filtered_batters["hit_OPS"].max()
    st.metric("OPS 최댓값", f"{max_ops_filt:.3f}" if pd.notna(max_ops_filt) else "N/A")

st.divider()

# ---------------------------------------------------------------
# 2. 기술통계표
# ---------------------------------------------------------------
st.subheader("2️⃣ 기술통계표 (N, 평균, 표준편차, 최솟값, 중앙값, 최댓값)")
st.caption(f"표본: PA ≥ {min_pa} 타자, {year_choice}")

metrics = {"hit_AVG": "타율(AVG)", "hit_OBP": "출루율(OBP)", "hit_SLG": "장타율(SLG)",
           "hit_OPS": "OPS", "hit_HR": "홈런(HR)"}

desc_rows = []
for col, label in metrics.items():
    s = filtered_batters[col].dropna()
    if s.empty:
        continue
    desc_rows.append({
        "지표": label, "N": len(s), "평균(mean)": s.mean(), "표준편차(sd)": s.std(),
        "최솟값(min)": s.min(), "중앙값(p50)": s.median(), "최댓값(max)": s.max(),
        "평균-중앙값 차이": s.mean() - s.median(), "왜도(skewness)": s.skew(),
    })
desc_df = pd.DataFrame(desc_rows)

st.dataframe(
    desc_df, use_container_width=True, hide_index=True,
    column_config={
        c: st.column_config.NumberColumn(c, format="%.3f")
        for c in ["평균(mean)", "표준편차(sd)", "최솟값(min)", "중앙값(p50)", "최댓값(max)", "평균-중앙값 차이", "왜도(skewness)"]
    },
)

if not desc_df.empty:
    max_gap_row = desc_df.loc[desc_df["평균-중앙값 차이"].abs().idxmax()]
    st.info(
        f"📌 **평균과 중앙값 차이가 가장 큰 지표는 {max_gap_row['지표']}입니다** "
        f"(차이={max_gap_row['평균-중앙값 차이']:+.3f}, 왜도={max_gap_row['왜도(skewness)']:.2f}). "
        "오른쪽으로 꼬리가 긴 분포일수록 평균이 중앙값보다 커지는 경향이 있습니다 — "
        "이런 지표는 평균만으로 '대표값'을 판단하면 오해할 수 있습니다."
    )

st.divider()

# ---------------------------------------------------------------
# 3. 히스토그램 비교
# ---------------------------------------------------------------
st.subheader("3️⃣ 히스토그램으로 분포 비교")

hist_metrics = ["hit_OPS", "hit_HR", "hit_AVG"]
hist_labels = ["OPS", "홈런(HR)", "타율(AVG)"]

fig = make_subplots(rows=1, cols=3, subplot_titles=hist_labels)
for i, (col, label) in enumerate(zip(hist_metrics, hist_labels)):
    s = filtered_batters[col].dropna()
    fig.add_trace(
        go.Histogram(x=s, nbinsx=30, marker_color=COLOR_SEQUENCE[i], showlegend=False),
        row=1, col=i + 1,
    )
apply_common_layout(fig, height=380)
fig.update_annotations(font=dict(color="#111827", size=13))
st.plotly_chart(fig, use_container_width=True, theme=None)

st.markdown("""
**생각해볼 질문**
- 세 변수 중 어떤 분포가 정규분포(종 모양)에 가장 가까운가요?
- 어떤 변수에서 극단값(긴 꼬리)이 가장 많이 관찰되나요?
- 평균이 그 변수의 '대표값'으로 적절한가요, 아니면 중앙값이 더 나을까요?
""")
