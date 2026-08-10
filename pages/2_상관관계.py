"""
pages/2_상관관계.py
---------------------
과제 연계형 기초통계 페이지 (2/2): 상관관계 + 집단 비교
- OPS 구성요소(OBP, SLG) 상관관계 - "정의(공식)에 의한 관계"라는 함정 명시
- 홈런(HR)과 OPS의 관계
- 팀별 공격력 비교 (특정 연도)
- 시대별 비교 (2001-2009 / 2010-2019 / 2020-2025) + ANOVA
- (선택) 투수 버전: ERA와 관련 지표 상관관계
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from scipy import stats

from utils.data_loader import load_data, get_years, get_teams
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import render_glossary

st.set_page_config(page_title="기초통계 2: 상관관계와 집단비교", page_icon="🔗", layout="wide")

df = load_data()
years = get_years(df)

st.title("🔗 기초통계 (2/2): 상관관계와 집단 비교")
st.caption("Part 1과 동일하게 분석 대상은 **타자**로 한정합니다.")
render_glossary(["hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS", "pit_ERA", "pit_WHIP", "pit_K9", "pit_BB9"])

# ---------------------------------------------------------------
# 표본 설정 (Part 1과 동일한 로직, 이 페이지 전체에 적용)
# ---------------------------------------------------------------
col_a, col_b = st.columns([1, 1.5])
with col_a:
    latest_year = years[-1]
    year_choice = st.selectbox("연도 선택 (팀별 비교에 사용)", options=years, index=len(years) - 1)
with col_b:
    min_pa = st.slider("최소 타석(PA) 기준", min_value=0, max_value=300, value=100, step=10, key="min_pa_p2")

base_all = df[df["hit_PA"] >= min_pa].dropna(subset=["hit_OPS", "hit_OBP", "hit_SLG"]).copy()
st.caption(f"전체 기간 기준 분석 표본: **{len(base_all):,}명-시즌** (PA≥{min_pa})")

st.divider()

# ---------------------------------------------------------------
# 1. OPS의 구성요소
# ---------------------------------------------------------------
st.subheader("1️⃣ OPS의 구성요소: 출루율(OBP)과 장타율(SLG)")
st.warning(
    "⚠️ **OPS = OBP + SLG는 정의(공식)에 의한 관계**입니다. 따라서 상관계수가 높게 나오는 건 "
    "'우연히 함께 움직여서'가 아니라 '애초에 더해서 만든 값'이기 때문입니다. "
    "이걸 인과관계처럼 해석하면 안 됩니다 — 오히려 이 자체가 좋은 교육 포인트입니다."
)

pair_options = {
    "OPS ↔ OBP": ("hit_OPS", "hit_OBP"),
    "OPS ↔ SLG": ("hit_OPS", "hit_SLG"),
    "OBP ↔ SLG": ("hit_OBP", "hit_SLG"),
}
corr_rows = []
for label, (a, b) in pair_options.items():
    r, p = stats.pearsonr(base_all[a], base_all[b])
    corr_rows.append({"비교": label, "상관계수(r)": r, "p-value": p})
st.dataframe(
    pd.DataFrame(corr_rows), use_container_width=True, hide_index=True,
    column_config={
        "상관계수(r)": st.column_config.NumberColumn("상관계수(r)", format="%.3f"),
        "p-value": st.column_config.NumberColumn("p-value", format="%.4f"),
    },
)

pair_choice = st.selectbox("산점도로 확인할 조합 선택", options=list(pair_options.keys()))
a_col, b_col = pair_options[pair_choice]

fig_scatter = go.Figure()
fig_scatter.add_trace(go.Scatter(
    x=base_all[a_col], y=base_all[b_col], mode="markers",
    marker=dict(color=COLOR_SEQUENCE[0], size=6, opacity=0.5),
))
slope, intercept = np.polyfit(base_all[a_col], base_all[b_col], 1)
x_line = np.array([base_all[a_col].min(), base_all[a_col].max()])
fig_scatter.add_trace(go.Scatter(
    x=x_line, y=slope * x_line + intercept, mode="lines",
    line=dict(color=COLOR_SEQUENCE[3], width=3), name="추세선",
))
fig_scatter.update_xaxes(title=pair_choice.split(" ↔ ")[0])
fig_scatter.update_yaxes(title=pair_choice.split(" ↔ ")[1])
apply_common_layout(fig_scatter, height=440)
st.plotly_chart(fig_scatter, use_container_width=True, theme=None)

st.divider()

# ---------------------------------------------------------------
# 2. 홈런과 OPS의 관계
# ---------------------------------------------------------------
st.subheader("2️⃣ 홈런(HR)과 OPS의 관계")

hr_ops = base_all.dropna(subset=["hit_HR"])
r_hr, p_hr = stats.pearsonr(hr_ops["hit_HR"], hr_ops["hit_OPS"])

c1, c2, c3 = st.columns(3)
c1.metric("홈런 평균 ± SD", f"{hr_ops['hit_HR'].mean():.1f} ± {hr_ops['hit_HR'].std():.1f}")
c2.metric("OPS 평균 ± SD", f"{hr_ops['hit_OPS'].mean():.3f} ± {hr_ops['hit_OPS'].std():.3f}")
c3.metric("상관계수(r)", f"{r_hr:.3f}", help=f"p={p_hr:.4f}")

fig_hr = go.Figure()
fig_hr.add_trace(go.Scatter(
    x=hr_ops["hit_HR"], y=hr_ops["hit_OPS"], mode="markers",
    marker=dict(color=COLOR_SEQUENCE[2], size=6, opacity=0.5),
))
slope_hr, intercept_hr = np.polyfit(hr_ops["hit_HR"], hr_ops["hit_OPS"], 1)
x_line_hr = np.array([hr_ops["hit_HR"].min(), hr_ops["hit_HR"].max()])
fig_hr.add_trace(go.Scatter(
    x=x_line_hr, y=slope_hr * x_line_hr + intercept_hr, mode="lines",
    line=dict(color=COLOR_SEQUENCE[3], width=3), name="추세선",
))
fig_hr.update_xaxes(title="홈런(HR)")
fig_hr.update_yaxes(title="OPS")
apply_common_layout(fig_hr, height=440)
st.plotly_chart(fig_hr, use_container_width=True, theme=None)

st.info(
    "📌 **생각해보기**: 홈런이 많은 선수가 반드시 OPS도 높을까요? 상관계수가 1이 아닌 이유는 무엇일까요? "
    "(힌트: 출루율, 안타 수, 타석 수 등 OPS에 영향을 주는 다른 요인들이 있습니다)"
)

st.divider()

# ---------------------------------------------------------------
# 3. 팀별 공격력 비교
# ---------------------------------------------------------------
st.subheader(f"3️⃣ 팀별 공격력 비교 ({year_choice}년)")

team_season = base_all[base_all["year"] == year_choice]
if not team_season.empty:
    team_stats = (
        team_season.groupby("team")["hit_OPS"]
        .agg(N="count", 평균="mean", 표준편차="std", 최솟값="min", 최댓값="max")
        .reset_index()
        .sort_values("평균", ascending=False)
    )
    team_stats.insert(1, "순위", range(1, len(team_stats) + 1))

    st.dataframe(
        team_stats, use_container_width=True, hide_index=True,
        column_config={
            "team": st.column_config.TextColumn("구단"),
            "평균": st.column_config.NumberColumn("평균 OPS", format="%.3f"),
            "표준편차": st.column_config.NumberColumn("표준편차", format="%.3f"),
            "최솟값": st.column_config.NumberColumn("최솟값", format="%.3f"),
            "최댓값": st.column_config.NumberColumn("최댓값", format="%.3f"),
        },
    )

    gap = team_stats["평균"].max() - team_stats["평균"].min()
    best_team = team_stats.iloc[0]["team"]
    worst_team = team_stats.iloc[-1]["team"]
    st.metric(f"{year_choice}년 팀별 평균 OPS 최대−최소 차이", f"{gap:.3f}",
              help=f"최고: {best_team}, 최저: {worst_team}")

    fig_team_box = go.Figure()
    order = team_stats["team"].tolist()
    for t in order:
        fig_team_box.add_trace(go.Box(
            y=team_season[team_season["team"] == t]["hit_OPS"], name=t,
            marker_color=COLOR_SEQUENCE[0], boxpoints=False,
        ))
    fig_team_box.update_yaxes(title="OPS")
    apply_common_layout(fig_team_box, height=440)
    st.plotly_chart(fig_team_box, use_container_width=True, theme=None)
else:
    st.info("선택한 연도에 해당하는 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# 4. 시대별 비교
# ---------------------------------------------------------------
st.subheader("4️⃣ 시대별 비교 (2001–2009 / 2010–2019 / 2020–2025)")


def to_era(y):
    if y <= 2009:
        return "2001–2009"
    elif y <= 2019:
        return "2010–2019"
    return "2020–2025"


era_order = ["2001–2009", "2010–2019", "2020–2025"]
era_data = base_all.copy()
era_data["시대"] = era_data["year"].apply(to_era)

era_stats = (
    era_data.groupby("시대")["hit_OPS"].agg(N="count", 평균="mean", 표준편차="std")
    .reindex(era_order).reset_index()
)
st.dataframe(
    era_stats, use_container_width=True, hide_index=True,
    column_config={
        "평균": st.column_config.NumberColumn("평균 OPS", format="%.3f"),
        "표준편차": st.column_config.NumberColumn("표준편차", format="%.3f"),
    },
)

groups = [era_data[era_data["시대"] == e]["hit_OPS"].dropna() for e in era_order]
groups = [g for g in groups if len(g) >= 2]

if len(groups) == 3:
    f_stat, p_val = stats.f_oneway(*groups)
    m1, m2 = st.columns(2)
    m1.metric("ANOVA F-통계량", f"{f_stat:.3f}")
    m2.metric("p-value", f"{p_val:.4f}")

    fig_era = go.Figure()
    for e in era_order:
        fig_era.add_trace(go.Box(
            y=era_data[era_data["시대"] == e]["hit_OPS"], name=e,
            marker_color=COLOR_SEQUENCE[1], boxpoints=False,
        ))
    fig_era.update_yaxes(title="OPS")
    apply_common_layout(fig_era, height=440)
    st.plotly_chart(fig_era, use_container_width=True, theme=None)

    if p_val < 0.05:
        st.success(f"📌 p={p_val:.4f} < 0.05 → 세 시대 간 평균 OPS 차이는 **통계적으로 유의**합니다.")
    else:
        st.info(f"📌 p={p_val:.4f} ≥ 0.05 → 세 시대 간 평균 OPS 차이가 통계적으로 유의하다고 보기 어렵습니다.")
else:
    st.warning("일부 시대 구간의 표본이 부족해 ANOVA를 수행할 수 없습니다.")

st.divider()

# ---------------------------------------------------------------
# 5. (선택) 투수 버전
# ---------------------------------------------------------------
with st.expander("⚾ (심화·선택) 투수 버전: ERA가 낮은 투수는 어떤 특징을 가지는가?"):
    st.caption("최소 이닝(IP≥30) 기준을 적용한 투수 표본입니다.")

    pitcher_base = df[(df["primary_position"] == "투수") & (df["pit_IP"] >= 30)].dropna(subset=["pit_ERA"])
    pit_pairs = {
        "ERA ↔ WHIP": ("pit_ERA", "pit_WHIP"),
        "ERA ↔ 피OPS": ("pit_ERA", "pit_OPS"),
        "ERA ↔ K/9": ("pit_ERA", "pit_K9"),
        "ERA ↔ BB/9": ("pit_ERA", "pit_BB9"),
    }
    pit_rows = []
    for label, (a, b) in pit_pairs.items():
        sub = pitcher_base.dropna(subset=[a, b])
        if len(sub) >= 3:
            r, p = stats.pearsonr(sub[a], sub[b])
            pit_rows.append({"비교": label, "상관계수(r)": r, "p-value": p, "N": len(sub)})
    if pit_rows:
        st.dataframe(
            pd.DataFrame(pit_rows), use_container_width=True, hide_index=True,
            column_config={
                "상관계수(r)": st.column_config.NumberColumn("상관계수(r)", format="%.3f"),
                "p-value": st.column_config.NumberColumn("p-value", format="%.4f"),
            },
        )
        st.caption("💡 어떤 지표가 ERA와 가장 강한 상관관계를 보이나요? (참고: WHIP·피OPS는 ERA와 계산 구조가 밀접하게 얽혀있습니다)")
    else:
        st.info("표시할 데이터가 부족합니다.")
