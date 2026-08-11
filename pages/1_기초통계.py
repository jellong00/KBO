"""
pages/1_기초통계.py
---------------------
과제 연계형 기초통계 페이지 (1/2): 기술통계표 + 분포
- 🏏 타자 탭: AVG/OBP/SLG/OPS/HR, 최소 타석(PA) 기준
- ⚾ 투수 탭: ERA/WHIP/K9/BB9/SO, 최소 이닝(IP) 기준
각 탭 동일 구조: 표본설정 → 표본제한 필요성 → 기술통계표 → 단순/가중평균
→ 히스토그램 → 박스플롯 → 표본기준 민감도
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


def skew_interpretation(sk):
    if sk > 1:
        return "오른쪽 꼬리(양의 왜도) — 소수의 매우 높은 값이 평균을 끌어올림"
    elif sk < -1:
        return "왼쪽 꼬리(음의 왜도) — 소수의 매우 낮은 값이 평균을 끌어내림"
    return "비교적 대칭적"


st.title("📊 기초통계 (1/2): 기술통계표와 분포")
tab_batter, tab_pitcher = st.tabs(["🏏 타자", "⚾ 투수"])

# =================================================================
# 🏏 타자 탭
# =================================================================
with tab_batter:
    st.caption("분석 대상: **타자**. 투수 지표는 다루지 않습니다.")
    render_glossary(["hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS"])

    st.subheader("0️⃣ 분석 표본 설정")
    col_a, col_b = st.columns([1, 1.5])
    with col_a:
        b_year_choice = st.selectbox("연도 선택", options=["전체 기간"] + years, index=0, key="b_year")
    with col_b:
        b_min = st.slider(
            "최소 타석(PA) 기준", min_value=0, max_value=300, value=100, step=10, key="b_min_pa",
            help="분석자가 임의로 설정하는 표본 제한 기준입니다. KBO 공식 '규정타석'과는 다릅니다.",
        )
    st.caption(f"⚠️ PA≥{b_min}은 **분석자가 설정한 표본 제한 기준**입니다. KBO 공식 규정타석과는 다른 개념입니다.")

    b_base = df[df["hit_PA"].notna()].copy()
    if b_year_choice != "전체 기간":
        b_base = b_base[b_base["year"] == b_year_choice]
    b_all = b_base.copy()
    b_filtered = b_base[b_base["hit_PA"] >= b_min].copy()
    st.caption(f"전체: **{len(b_all):,}개 선수-시즌 관측치** · 필터 후(PA≥{b_min}): **{len(b_filtered):,}개**")

    st.divider()
    st.subheader("1️⃣ 왜 표본 크기 기준이 필요한가?")
    st.caption("타석 수가 매우 적으면, 표본이 작아 우연의 영향을 크게 받는 극단값이 나타날 수 있습니다.")

    b_extreme = b_all[b_all["hit_PA"] < 20].dropna(subset=["hit_AVG"]).sort_values("hit_AVG", ascending=False).head(8)
    if not b_extreme.empty:
        st.dataframe(
            b_extreme[["player_name", "year", "team", "hit_PA", "hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS", "hit_HR"]],
            use_container_width=True, hide_index=True,
            column_config={
                "hit_AVG": st.column_config.NumberColumn("타율", format="%.3f"),
                "hit_OBP": st.column_config.NumberColumn("출루율", format="%.3f"),
                "hit_SLG": st.column_config.NumberColumn("장타율", format="%.3f"),
                "hit_OPS": st.column_config.NumberColumn("OPS", format="%.3f"),
            },
        )
        st.warning("표본이 작으면 우연에 의한 극단값이 섞여 들어갑니다. 표본 제한 기준은 이를 걸러내기 위한 장치입니다.")

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**A. 전체 (필터 없음)**")
        st.metric("표본 크기", f"{len(b_all):,}개")
        v = b_all["hit_OPS"].max()
        st.metric("OPS 최댓값", f"{v:.3f}" if pd.notna(v) else "N/A")
    with cc2:
        st.markdown(f"**B. PA ≥ {b_min} 필터**")
        st.metric("표본 크기", f"{len(b_filtered):,}개")
        v = b_filtered["hit_OPS"].max()
        st.metric("OPS 최댓값", f"{v:.3f}" if pd.notna(v) else "N/A")

    st.divider()
    st.subheader("2️⃣ 기술통계표")
    st.caption("N은 '선수 수'가 아니라 **'선수-시즌 관측치 수'**입니다.")

    b_metrics = {"hit_AVG": "타율(AVG)", "hit_OBP": "출루율(OBP)", "hit_SLG": "장타율(SLG)",
                 "hit_OPS": "OPS", "hit_HR": "홈런(HR)"}
    b_rows = []
    for col, label in b_metrics.items():
        s = b_filtered[col].dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        b_rows.append({
            "지표": label, "N": len(s), "평균(mean)": s.mean(), "표준편차(sd)": s.std(),
            "최솟값(min)": s.min(), "p25": q1, "중앙값(p50)": s.median(), "p75": q3,
            "IQR(p75-p25)": q3 - q1, "최댓값(max)": s.max(), "왜도(skewness)": s.skew(),
            "분포 해석": skew_interpretation(s.skew()),
        })
    b_desc = pd.DataFrame(b_rows)
    num_cols = ["평균(mean)", "표준편차(sd)", "최솟값(min)", "p25", "중앙값(p50)", "p75", "IQR(p75-p25)", "최댓값(max)", "왜도(skewness)"]
    st.dataframe(b_desc, use_container_width=True, hide_index=True,
                 column_config={c: st.column_config.NumberColumn(c, format="%.3f") for c in num_cols})
    st.caption("💡 각 지표의 평균·중앙값은 그 지표 **내부에서만** 비교하세요 (단위가 다른 지표끼리 직접 비교는 부적절). N이 다르면 결측치 때문일 수 있습니다.")

    st.divider()
    st.subheader("3️⃣ 단순평균 vs 타석(PA) 가중평균")
    b_weight_rows = []
    for col, label in b_metrics.items():
        if col == "hit_HR":
            continue
        sub = b_filtered.dropna(subset=[col, "hit_PA"])
        if sub.empty:
            continue
        simple_mean = sub[col].mean()
        weighted_mean = np.average(sub[col], weights=sub["hit_PA"])
        b_weight_rows.append({"지표": label, "단순평균": simple_mean, "PA 가중평균": weighted_mean,
                               "차이(가중-단순)": weighted_mean - simple_mean})
    st.dataframe(pd.DataFrame(b_weight_rows), use_container_width=True, hide_index=True,
                 column_config={c: st.column_config.NumberColumn(c, format="%.4f") for c in ["단순평균", "PA 가중평균", "차이(가중-단순)"]})

    st.divider()
    st.subheader("4️⃣ 히스토그램으로 분포 비교")
    b_hist_cols, b_hist_labels = ["hit_OPS", "hit_HR", "hit_AVG"], ["OPS", "홈런(HR)", "타율(AVG)"]
    fig_b_hist = make_subplots(rows=1, cols=3, subplot_titles=b_hist_labels)
    for i, (col, label) in enumerate(zip(b_hist_cols, b_hist_labels)):
        s = b_filtered[col].dropna()
        fig_b_hist.add_trace(go.Histogram(x=s, nbinsx=30, marker_color=COLOR_SEQUENCE[i], showlegend=False), row=1, col=i + 1)
        fig_b_hist.add_vline(x=s.mean(), line_color="#111827", line_width=2, row=1, col=i + 1)
        fig_b_hist.add_vline(x=s.median(), line_color="#111827", line_width=2, line_dash="dash", row=1, col=i + 1)
    apply_common_layout(fig_b_hist, height=380)
    fig_b_hist.update_annotations(font=dict(color="#111827", size=13))
    st.plotly_chart(fig_b_hist, use_container_width=True, theme=None)
    st.caption("실선=평균, 점선=중앙값.")

    st.divider()
    st.subheader("5️⃣ 박스플롯으로 IQR과 이상치 확인하기")
    b_box_label = st.selectbox("박스플롯 지표 선택", options=["OPS", "홈런(HR)"], key="b_box")
    b_box_col = "hit_OPS" if b_box_label == "OPS" else "hit_HR"
    fig_b_box = go.Figure(go.Box(y=b_filtered[b_box_col].dropna(), marker_color=COLOR_SEQUENCE[0], boxpoints="outliers", name=b_box_label))
    fig_b_box.update_yaxes(title=b_box_label)
    apply_common_layout(fig_b_box, height=440)
    st.plotly_chart(fig_b_box, use_container_width=True, theme=None)

    st.divider()
    st.subheader("6️⃣ PA 기준을 바꾸면 통계치가 어떻게 달라지는가?")
    b_sens_rows = []
    for pa_th in [0, 50, 100, 200]:
        sub = b_base[b_base["hit_PA"] >= pa_th]["hit_OPS"].dropna()
        if sub.empty:
            continue
        b_sens_rows.append({"PA 기준": f"≥{pa_th}", "N": len(sub), "평균(OPS)": sub.mean(),
                             "표준편차(OPS)": sub.std(), "최댓값(OPS)": sub.max()})
    st.dataframe(pd.DataFrame(b_sens_rows), use_container_width=True, hide_index=True,
                 column_config={c: st.column_config.NumberColumn(c, format="%.3f") for c in ["평균(OPS)", "표준편차(OPS)", "최댓값(OPS)"]})

# =================================================================
# ⚾ 투수 탭
# =================================================================
with tab_pitcher:
    st.caption("분석 대상: **투수** (`primary_position == '투수'`). 타자 지표는 다루지 않습니다.")
    render_glossary(["pit_ERA", "pit_WHIP", "pit_K9", "pit_BB9", "pit_SO"])

    st.subheader("0️⃣ 분석 표본 설정")
    col_a, col_b = st.columns([1, 1.5])
    with col_a:
        p_year_choice = st.selectbox("연도 선택", options=["전체 기간"] + years, index=0, key="p_year")
    with col_b:
        p_min = st.slider(
            "최소 이닝(IP) 기준", min_value=0, max_value=180, value=30, step=10, key="p_min_ip",
            help="분석자가 임의로 설정하는 표본 제한 기준입니다. KBO 공식 '규정이닝'과는 다릅니다.",
        )
    st.caption(f"⚠️ IP≥{p_min}은 **분석자가 설정한 표본 제한 기준**입니다. KBO 공식 규정이닝과는 다른 개념입니다.")

    p_base = df[(df["primary_position"] == "투수") & df["pit_IP"].notna()].copy()
    if p_year_choice != "전체 기간":
        p_base = p_base[p_base["year"] == p_year_choice]
    p_all = p_base.copy()
    p_filtered = p_base[p_base["pit_IP"] >= p_min].copy()
    st.caption(f"전체: **{len(p_all):,}개 투수-시즌 관측치** · 필터 후(IP≥{p_min}): **{len(p_filtered):,}개**")

    st.divider()
    st.subheader("1️⃣ 왜 표본 크기 기준이 필요한가?")
    st.caption("이닝 수가 매우 적으면, 표본이 작아 우연의 영향을 크게 받는 극단적인 ERA가 나타날 수 있습니다.")

    p_extreme = p_all[p_all["pit_IP"] < 5].dropna(subset=["pit_ERA"]).sort_values("pit_ERA", ascending=False).head(8)
    if not p_extreme.empty:
        st.dataframe(
            p_extreme[["player_name", "year", "team", "pit_IP", "pit_ERA", "pit_WHIP", "pit_SO"]],
            use_container_width=True, hide_index=True,
            column_config={
                "pit_IP": st.column_config.NumberColumn("이닝", format="%.1f"),
                "pit_ERA": st.column_config.NumberColumn("ERA", format="%.2f"),
                "pit_WHIP": st.column_config.NumberColumn("WHIP", format="%.2f"),
            },
        )
        st.warning("이닝이 몇 개 안 되는 상태에서 실점을 몇 번 하면 ERA가 비정상적으로 치솟습니다. 표본 제한 기준은 이를 걸러내기 위한 장치입니다.")

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**A. 전체 (필터 없음)**")
        st.metric("표본 크기", f"{len(p_all):,}개")
        v = p_all["pit_ERA"].max()
        st.metric("ERA 최댓값", f"{v:.2f}" if pd.notna(v) else "N/A")
    with cc2:
        st.markdown(f"**B. IP ≥ {p_min} 필터**")
        st.metric("표본 크기", f"{len(p_filtered):,}개")
        v = p_filtered["pit_ERA"].max()
        st.metric("ERA 최댓값", f"{v:.2f}" if pd.notna(v) else "N/A")

    st.divider()
    st.subheader("2️⃣ 기술통계표")
    st.caption("N은 '투수 수'가 아니라 **'투수-시즌 관측치 수'**입니다.")

    p_metrics = {"pit_ERA": "ERA", "pit_WHIP": "WHIP", "pit_K9": "K/9", "pit_BB9": "BB/9", "pit_SO": "탈삼진(SO)"}
    p_rows = []
    for col, label in p_metrics.items():
        s = p_filtered[col].dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        p_rows.append({
            "지표": label, "N": len(s), "평균(mean)": s.mean(), "표준편차(sd)": s.std(),
            "최솟값(min)": s.min(), "p25": q1, "중앙값(p50)": s.median(), "p75": q3,
            "IQR(p75-p25)": q3 - q1, "최댓값(max)": s.max(), "왜도(skewness)": s.skew(),
            "분포 해석": skew_interpretation(s.skew()),
        })
    p_desc = pd.DataFrame(p_rows)
    st.dataframe(p_desc, use_container_width=True, hide_index=True,
                 column_config={c: st.column_config.NumberColumn(c, format="%.3f") for c in num_cols})
    st.caption("💡 ERA·WHIP는 낮을수록 좋은 지표이므로, 왜도가 양수(오른쪽 꼬리)라면 '부진한 소수 투수'가 평균을 끌어올린 것으로 해석할 수 있습니다.")

    st.divider()
    st.subheader("3️⃣ 단순평균 vs 이닝(IP) 가중평균")
    p_weight_rows = []
    for col, label in p_metrics.items():
        if col == "pit_SO":
            continue
        sub = p_filtered.dropna(subset=[col, "pit_IP"])
        if sub.empty:
            continue
        simple_mean = sub[col].mean()
        weighted_mean = np.average(sub[col], weights=sub["pit_IP"])
        p_weight_rows.append({"지표": label, "단순평균": simple_mean, "IP 가중평균": weighted_mean,
                               "차이(가중-단순)": weighted_mean - simple_mean})
    st.dataframe(pd.DataFrame(p_weight_rows), use_container_width=True, hide_index=True,
                 column_config={c: st.column_config.NumberColumn(c, format="%.4f") for c in ["단순평균", "IP 가중평균", "차이(가중-단순)"]})
    st.caption("💡 많이 던진 투수(주로 선발급)와 적게 던진 투수(불펜/추격조)의 성적 경향이 다르면 두 평균의 차이가 커집니다.")

    st.divider()
    st.subheader("4️⃣ 히스토그램으로 분포 비교")
    p_hist_cols, p_hist_labels = ["pit_ERA", "pit_SO", "pit_WHIP"], ["ERA", "탈삼진(SO)", "WHIP"]
    fig_p_hist = make_subplots(rows=1, cols=3, subplot_titles=p_hist_labels)
    for i, (col, label) in enumerate(zip(p_hist_cols, p_hist_labels)):
        s = p_filtered[col].dropna()
        fig_p_hist.add_trace(go.Histogram(x=s, nbinsx=30, marker_color=COLOR_SEQUENCE[i], showlegend=False), row=1, col=i + 1)
        fig_p_hist.add_vline(x=s.mean(), line_color="#111827", line_width=2, row=1, col=i + 1)
        fig_p_hist.add_vline(x=s.median(), line_color="#111827", line_width=2, line_dash="dash", row=1, col=i + 1)
    apply_common_layout(fig_p_hist, height=380)
    fig_p_hist.update_annotations(font=dict(color="#111827", size=13))
    st.plotly_chart(fig_p_hist, use_container_width=True, theme=None)
    st.caption("실선=평균, 점선=중앙값.")

    st.divider()
    st.subheader("5️⃣ 박스플롯으로 IQR과 이상치 확인하기")
    p_box_label = st.selectbox("박스플롯 지표 선택", options=["ERA", "탈삼진(SO)"], key="p_box")
    p_box_col = "pit_ERA" if p_box_label == "ERA" else "pit_SO"
    fig_p_box = go.Figure(go.Box(y=p_filtered[p_box_col].dropna(), marker_color=COLOR_SEQUENCE[1], boxpoints="outliers", name=p_box_label))
    fig_p_box.update_yaxes(title=p_box_label)
    apply_common_layout(fig_p_box, height=440)
    st.plotly_chart(fig_p_box, use_container_width=True, theme=None)

    st.divider()
    st.subheader("6️⃣ IP 기준을 바꾸면 통계치가 어떻게 달라지는가?")
    p_sens_rows = []
    for ip_th in [0, 30, 60, 100]:
        sub = p_base[p_base["pit_IP"] >= ip_th]["pit_ERA"].dropna()
        if sub.empty:
            continue
        p_sens_rows.append({"IP 기준": f"≥{ip_th}", "N": len(sub), "평균(ERA)": sub.mean(),
                             "표준편차(ERA)": sub.std(), "최댓값(ERA)": sub.max()})
    st.dataframe(pd.DataFrame(p_sens_rows), use_container_width=True, hide_index=True,
                 column_config={c: st.column_config.NumberColumn(c, format="%.3f") for c in ["평균(ERA)", "표준편차(ERA)", "최댓값(ERA)"]})
