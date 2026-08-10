"""
pages/2_상관관계.py
---------------------
과제 연계형 기초통계 페이지 (2/2): 상관관계 + 집단 비교
1️⃣ 상관관계의 기초: HR↔OPS, BB↔OBP, SO↔AVG, HR↔SO (Pearson r + 산점도 + 추세선)
2️⃣ 팀별 공격력 비교: 팀별 N/평균/SD + 평균 OPS ± 95% CI dot plot
3️⃣ 시대별 공격력 비교: 시대별 N/평균/SD + 평균 ± 95% CI + One-way ANOVA
4️⃣ (선택) 투수 상관관계: ERA-WHIP, ERA-피OPS, ERA-K/9, ERA-BB/9
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from scipy import stats

from utils.data_loader import load_data, get_years
from utils.style import apply_common_layout, COLOR_SEQUENCE
from utils.glossary import render_glossary

st.set_page_config(page_title="기초통계 2: 상관관계와 집단비교", page_icon="🔗", layout="wide")

df = load_data()
years = get_years(df)

st.title("🔗 기초통계 (2/2): 상관관계와 집단 비교")
st.caption("Part 1과 동일하게 분석 대상은 **타자**로 한정합니다.")
render_glossary(["hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS", "pit_ERA", "pit_WHIP", "pit_K9", "pit_BB9"])

# ---------------------------------------------------------------
# 표본 설정 (이 페이지 전체에 적용)
# ---------------------------------------------------------------
col_a, col_b = st.columns([1, 1.5])
with col_a:
    year_choice = st.selectbox("연도 선택 (팀별 비교에 사용)", options=years, index=len(years) - 1)
with col_b:
    min_pa = st.slider("최소 타석(PA) 기준", min_value=0, max_value=300, value=100, step=10, key="min_pa_p2")

base_all = df[df["hit_PA"] >= min_pa].copy()
st.caption(f"전체 기간 기준 분석 표본: **{len(base_all):,}개 선수-시즌 관측치** (PA≥{min_pa})")

st.divider()

# ---------------------------------------------------------------
# 1. 상관관계의 기초
# ---------------------------------------------------------------
st.subheader("1️⃣ 상관관계의 기초")

pair_options = {
    "홈런(HR) ↔ OPS": ("hit_HR", "hit_OPS"),
    "볼넷(BB) ↔ 출루율(OBP)": ("hit_BB", "hit_OBP"),
    "삼진(SO) ↔ 타율(AVG)": ("hit_SO", "hit_AVG"),
    "홈런(HR) ↔ 삼진(SO)": ("hit_HR", "hit_SO"),
}

corr_rows = []
for label, (a, b) in pair_options.items():
    sub = base_all.dropna(subset=[a, b])
    if len(sub) >= 3:
        r, p = stats.pearsonr(sub[a], sub[b])
        corr_rows.append({"비교": label, "상관계수(r)": r, "p-value": p, "N": len(sub)})

st.dataframe(
    pd.DataFrame(corr_rows), use_container_width=True, hide_index=True,
    column_config={
        "상관계수(r)": st.column_config.NumberColumn("상관계수(r)", format="%.3f"),
        "p-value": st.column_config.NumberColumn("p-value", format="%.4f"),
    },
)

pair_choice = st.selectbox("산점도로 확인할 조합 선택", options=list(pair_options.keys()))
a_col, b_col = pair_options[pair_choice]
scatter_data = base_all.dropna(subset=[a_col, b_col])

fig_scatter = go.Figure()
fig_scatter.add_trace(go.Scatter(
    x=scatter_data[a_col], y=scatter_data[b_col], mode="markers",
    marker=dict(color=COLOR_SEQUENCE[0], size=6, opacity=0.5),
))
slope, intercept = np.polyfit(scatter_data[a_col], scatter_data[b_col], 1)
x_line = np.array([scatter_data[a_col].min(), scatter_data[a_col].max()])
fig_scatter.add_trace(go.Scatter(
    x=x_line, y=slope * x_line + intercept, mode="lines",
    line=dict(color=COLOR_SEQUENCE[3], width=3), name="추세선",
))
fig_scatter.update_xaxes(title=pair_choice.split(" ↔ ")[0])
fig_scatter.update_yaxes(title=pair_choice.split(" ↔ ")[1])
apply_common_layout(fig_scatter, height=440)
st.plotly_chart(fig_scatter, use_container_width=True, theme=None)

st.markdown("""
**핵심 질문**
- 상관계수의 부호(+/−)와 크기는 무엇을 의미하나요?
- 산점도에서 선형 관계가 실제로 눈에 보이나요?
- 이 관계를 인과관계라고 해석할 수 있을까요? (상관관계 ≠ 인과관계)
""")

st.divider()

# ---------------------------------------------------------------
# 2. 팀별 공격력 비교
# ---------------------------------------------------------------
st.subheader(f"2️⃣ 팀별 공격력 비교 ({year_choice}년)")

team_season = base_all[base_all["year"] == year_choice].dropna(subset=["hit_OPS"])

if not team_season.empty:
    team_rows = []
    for t, g in team_season.groupby("team"):
        n = len(g)
        if n < 2:
            continue
        mean_v = g["hit_OPS"].mean()
        sd_v = g["hit_OPS"].std()
        se_v = sd_v / np.sqrt(n)
        ci = stats.t.ppf(0.975, df=n - 1) * se_v
        team_rows.append({"team": t, "N": n, "평균": mean_v, "표준편차": sd_v, "95% CI 반경": ci})

    team_stats = pd.DataFrame(team_rows).sort_values("평균", ascending=False).reset_index(drop=True)
    team_stats.insert(1, "순위", range(1, len(team_stats) + 1))

    st.dataframe(
        team_stats, use_container_width=True, hide_index=True,
        column_config={
            "team": st.column_config.TextColumn("구단"),
            "평균": st.column_config.NumberColumn("평균 OPS", format="%.3f"),
            "표준편차": st.column_config.NumberColumn("표준편차", format="%.3f"),
            "95% CI 반경": st.column_config.NumberColumn("95% CI 반경(±)", format="%.3f"),
        },
    )

    gap = team_stats["평균"].max() - team_stats["평균"].min()
    best_team, worst_team = team_stats.iloc[0]["team"], team_stats.iloc[-1]["team"]
    st.metric(f"{year_choice}년 팀별 평균 OPS 최대−최소 차이", f"{gap:.3f}",
              help=f"최고: {best_team}, 최저: {worst_team}")

    # 평균 ± 95% CI dot plot (가로형, 평균 높은 순)
    plot_order = team_stats.sort_values("평균")  # 아래→위로 갈수록 평균 높게 보이도록
    fig_dot = go.Figure()
    fig_dot.add_trace(go.Scatter(
        x=plot_order["평균"], y=plot_order["team"], mode="markers",
        marker=dict(color=COLOR_SEQUENCE[0], size=10),
        error_x=dict(type="data", array=plot_order["95% CI 반경"], visible=True, color=COLOR_SEQUENCE[0]),
    ))
    fig_dot.update_xaxes(title="평균 OPS (± 95% 신뢰구간)")
    fig_dot.update_yaxes(title="")
    apply_common_layout(fig_dot, height=max(360, 32 * len(plot_order)))
    st.plotly_chart(fig_dot, use_container_width=True, theme=None)
    st.caption("점 = 팀 평균 OPS, 가로선 = 95% 신뢰구간. 신뢰구간이 넓을수록(팀 내 선수 편차가 크거나 N이 작을수록) 추정이 덜 정밀합니다.")
else:
    st.info("선택한 연도에 해당하는 데이터가 부족합니다.")

st.divider()

# ---------------------------------------------------------------
# 3. 시대별 공격력 비교
# ---------------------------------------------------------------
st.subheader("3️⃣ 시대별 공격력 비교 (2001–2009 / 2010–2019 / 2020–2025)")


def to_era(y):
    if y <= 2009:
        return "2001–2009"
    elif y <= 2019:
        return "2010–2019"
    return "2020–2025"


era_order = ["2001–2009", "2010–2019", "2020–2025"]
era_data = base_all.dropna(subset=["hit_OPS"]).copy()
era_data["시대"] = era_data["year"].apply(to_era)

era_rows = []
for e in era_order:
    g = era_data[era_data["시대"] == e]["hit_OPS"]
    n = len(g)
    if n < 2:
        continue
    mean_v, sd_v = g.mean(), g.std()
    se_v = sd_v / np.sqrt(n)
    ci = stats.t.ppf(0.975, df=n - 1) * se_v
    era_rows.append({"시대": e, "N": n, "평균": mean_v, "표준편차": sd_v, "95% CI 반경": ci})

era_stats = pd.DataFrame(era_rows)
st.dataframe(
    era_stats, use_container_width=True, hide_index=True,
    column_config={
        "평균": st.column_config.NumberColumn("평균 OPS", format="%.3f"),
        "표준편차": st.column_config.NumberColumn("표준편차", format="%.3f"),
        "95% CI 반경": st.column_config.NumberColumn("95% CI 반경(±)", format="%.3f"),
    },
)

if len(era_stats) == 3:
    fig_era_dot = go.Figure()
    fig_era_dot.add_trace(go.Scatter(
        x=era_stats["평균"], y=era_stats["시대"], mode="markers",
        marker=dict(color=COLOR_SEQUENCE[1], size=12),
        error_x=dict(type="data", array=era_stats["95% CI 반경"], visible=True, color=COLOR_SEQUENCE[1]),
    ))
    fig_era_dot.update_xaxes(title="평균 OPS (± 95% 신뢰구간)")
    fig_era_dot.update_yaxes(title="")
    apply_common_layout(fig_era_dot, height=320)
    st.plotly_chart(fig_era_dot, use_container_width=True, theme=None)

    groups = [era_data[era_data["시대"] == e]["hit_OPS"] for e in era_order]
    f_stat, p_val = stats.f_oneway(*groups)
    m1, m2 = st.columns(2)
    m1.metric("ANOVA F-통계량", f"{f_stat:.3f}")
    m2.metric("p-value", f"{p_val:.4f}")

    if p_val < 0.05:
        st.success(f"📌 p={p_val:.4f} < 0.05 → 세 시대 간 평균 OPS 차이는 **통계적으로 유의**합니다 (적어도 한 집단은 다릅니다).")
    else:
        st.info(f"📌 p={p_val:.4f} ≥ 0.05 → 세 시대 간 평균 OPS 차이가 통계적으로 유의하다고 보기 어렵습니다.")
else:
    st.warning("일부 시대 구간의 표본이 부족해 비교를 수행할 수 없습니다.")

st.divider()

# ---------------------------------------------------------------
# 4. (선택) 투수 상관관계
# ---------------------------------------------------------------
with st.expander("⚾ (심화·선택) 투수 상관관계: ERA가 낮은 투수는 어떤 특징을 가지는가?"):
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
