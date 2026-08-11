"""
pages/2_상관관계.py
---------------------
과제 연계형 기초통계 페이지 (2/2): 상관관계 + 집단 비교
🏏 타자 탭: HR↔OPS, BB↔OBP, SO↔AVG, HR↔SO / 팀별·시대별 OPS 비교(평균±95%CI, ANOVA)
⚾ 투수 탭: ERA↔WHIP, ERA↔K9, ERA↔BB9, ERA↔피안타율 / 팀별·시대별 ERA 비교(평균±95%CI, ANOVA)
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


def safe_scatter_with_trend(data, x_col, y_col, x_label, y_label, color):
    """데이터가 비어있거나 너무 적으면 안내만 표시, 아니면 산점도+추세선 반환"""
    sub = data.dropna(subset=[x_col, y_col])
    if len(sub) < 3:
        st.info("이 조합은 표시할 데이터가 부족합니다.")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub[x_col], y=sub[y_col], mode="markers",
        marker=dict(color=color, size=6, opacity=0.5),
    ))
    slope, intercept = np.polyfit(sub[x_col], sub[y_col], 1)
    x_line = np.array([sub[x_col].min(), sub[x_col].max()])
    fig.add_trace(go.Scatter(
        x=x_line, y=slope * x_line + intercept, mode="lines",
        line=dict(color=COLOR_SEQUENCE[3], width=3), name="추세선",
    ))
    fig.update_xaxes(title=x_label)
    fig.update_yaxes(title=y_label)
    apply_common_layout(fig, height=440)
    st.plotly_chart(fig, use_container_width=True, theme=None)


def mean_ci_dotplot(rows_df, value_col, label_col, color, ascending_is_better=False):
    """평균 ± 95% CI 가로형 dot plot"""
    order = rows_df.sort_values(value_col, ascending=ascending_is_better)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=order[value_col], y=order[label_col], mode="markers",
        marker=dict(color=color, size=10),
        error_x=dict(type="data", array=order["ci"], visible=True, color=color),
    ))
    apply_common_layout(fig, height=max(320, 32 * len(order)))
    st.plotly_chart(fig, use_container_width=True, theme=None)


def to_era(y):
    if y <= 2009:
        return "2001–2009"
    elif y <= 2019:
        return "2010–2019"
    return "2020–2025"


era_order = ["2001–2009", "2010–2019", "2020–2025"]


st.title("🔗 기초통계 (2/2): 상관관계와 집단 비교")
tab_batter, tab_pitcher = st.tabs(["🏏 타자", "⚾ 투수"])

# =================================================================
# 🏏 타자 탭
# =================================================================
with tab_batter:
    render_glossary(["hit_AVG", "hit_OBP", "hit_SLG", "hit_OPS"])

    col_a, col_b = st.columns([1, 1.5])
    with col_a:
        b_year = st.selectbox("연도 선택 (팀별 비교에 사용)", options=years, index=len(years) - 1, key="b_year_corr")
    with col_b:
        b_min_pa = st.slider("최소 타석(PA) 기준", min_value=0, max_value=300, value=100, step=10, key="b_min_pa_corr")

    b_base = df[df["hit_PA"] >= b_min_pa].copy()
    st.caption(f"전체 기간 기준 분석 표본: **{len(b_base):,}개 선수-시즌 관측치** (PA≥{b_min_pa})")

    st.divider()
    st.subheader("1️⃣ 상관관계의 기초")

    b_pairs = {
        "홈런(HR) ↔ OPS": ("hit_HR", "hit_OPS"),
        "볼넷(BB) ↔ 출루율(OBP)": ("hit_BB", "hit_OBP"),
        "삼진(SO) ↔ 타율(AVG)": ("hit_SO", "hit_AVG"),
        "홈런(HR) ↔ 삼진(SO)": ("hit_HR", "hit_SO"),
    }
    b_corr_rows = []
    for label, (a, c) in b_pairs.items():
        sub = b_base.dropna(subset=[a, c])
        if len(sub) >= 3:
            r, p = stats.pearsonr(sub[a], sub[c])
            b_corr_rows.append({"비교": label, "상관계수(r)": r, "p-value": p, "N": len(sub)})
    st.dataframe(
        pd.DataFrame(b_corr_rows), use_container_width=True, hide_index=True,
        column_config={
            "상관계수(r)": st.column_config.NumberColumn("상관계수(r)", format="%.3f"),
            "p-value": st.column_config.NumberColumn("p-value", format="%.4f"),
        },
    )

    b_pair_choice = st.selectbox("산점도로 확인할 조합 선택", options=list(b_pairs.keys()), key="b_pair")
    b_a, b_c = b_pairs[b_pair_choice]
    safe_scatter_with_trend(b_base, b_a, b_c, b_pair_choice.split(" ↔ ")[0], b_pair_choice.split(" ↔ ")[1], COLOR_SEQUENCE[0])

    st.markdown("""
**핵심 질문**
- 상관계수의 부호(+/−)와 크기는 무엇을 의미하나요?
- 산점도에서 선형 관계가 실제로 눈에 보이나요?
- 이 관계를 인과관계라고 해석할 수 있을까요? (상관관계 ≠ 인과관계)
""")

    st.divider()
    st.subheader(f"2️⃣ 팀별 공격력 비교 ({b_year}년)")

    b_team_season = b_base[(b_base["year"] == b_year)].dropna(subset=["hit_OPS"])
    if not b_team_season.empty:
        b_team_rows = []
        for t, g in b_team_season.groupby("team"):
            n = len(g)
            if n < 2:
                continue
            mean_v, sd_v = g["hit_OPS"].mean(), g["hit_OPS"].std()
            se_v = sd_v / np.sqrt(n)
            ci = stats.t.ppf(0.975, df=n - 1) * se_v
            b_team_rows.append({"team": t, "N": n, "평균": mean_v, "표준편차": sd_v, "ci": ci})
        b_team_stats = pd.DataFrame(b_team_rows).sort_values("평균", ascending=False).reset_index(drop=True)
        b_team_stats.insert(1, "순위", range(1, len(b_team_stats) + 1))

        st.dataframe(
            b_team_stats.drop(columns=["ci"]), use_container_width=True, hide_index=True,
            column_config={
                "team": st.column_config.TextColumn("구단"),
                "평균": st.column_config.NumberColumn("평균 OPS", format="%.3f"),
                "표준편차": st.column_config.NumberColumn("표준편차", format="%.3f"),
            },
        )
        gap = b_team_stats["평균"].max() - b_team_stats["평균"].min()
        st.metric(f"{b_year}년 팀별 평균 OPS 최대−최소 차이", f"{gap:.3f}",
                  help=f"최고: {b_team_stats.iloc[0]['team']}, 최저: {b_team_stats.iloc[-1]['team']}")
        mean_ci_dotplot(b_team_stats, "평균", "team", COLOR_SEQUENCE[0], ascending_is_better=True)
        st.caption("점 = 팀 평균 OPS, 가로선 = 95% 신뢰구간.")
    else:
        st.info("선택한 연도에 해당하는 데이터가 부족합니다.")

    st.divider()
    st.subheader("3️⃣ 포지션별 공격력 비교 (포수 / 내야수 / 외야수)")
    st.caption("범주형 집단(포지션)에 따라 연속형 변수(OPS)의 평균이 다른지 확인합니다 — ANOVA의 전형적인 활용 예시입니다. (지명타자는 수비 포지션이 없어 이 데이터에서는 구분되지 않습니다)")

    def position_group(pos):
        if pos == "포수":
            return "포수"
        if pos in ["1루수", "2루수", "3루수", "유격수"]:
            return "내야수"
        if pos in ["좌익수", "중견수", "우익수"]:
            return "외야수"
        return None

    pos_group_order = ["포수", "내야수", "외야수"]
    b_pos_data = b_base.dropna(subset=["hit_OPS", "primary_position"]).copy()
    b_pos_data["포지션군"] = b_pos_data["primary_position"].apply(position_group)
    b_pos_data = b_pos_data.dropna(subset=["포지션군"])

    b_pos_rows = []
    for g_name in pos_group_order:
        g = b_pos_data[b_pos_data["포지션군"] == g_name]["hit_OPS"]
        n = len(g)
        if n < 2:
            continue
        mean_v, sd_v = g.mean(), g.std()
        se_v = sd_v / np.sqrt(n)
        ci = stats.t.ppf(0.975, df=n - 1) * se_v
        b_pos_rows.append({"포지션군": g_name, "N": n, "평균": mean_v, "표준편차": sd_v, "ci": ci})
    b_pos_stats = pd.DataFrame(b_pos_rows)
    st.dataframe(
        b_pos_stats.drop(columns=["ci"]) if not b_pos_stats.empty else b_pos_stats,
        use_container_width=True, hide_index=True,
        column_config={
            "평균": st.column_config.NumberColumn("평균 OPS", format="%.3f"),
            "표준편차": st.column_config.NumberColumn("표준편차", format="%.3f"),
        },
    )
    if len(b_pos_stats) == 3:
        mean_ci_dotplot(b_pos_stats, "평균", "포지션군", COLOR_SEQUENCE[1], ascending_is_better=True)
        groups = [b_pos_data[b_pos_data["포지션군"] == g]["hit_OPS"] for g in pos_group_order]
        f_stat, p_val = stats.f_oneway(*groups)
        m1, m2 = st.columns(2)
        m1.metric("ANOVA F-통계량", f"{f_stat:.3f}")
        m2.metric("p-value", f"{p_val:.4f}")
        if p_val < 0.05:
            st.success(f"📌 p={p_val:.4f} < 0.05 → 포지션군에 따라 평균 OPS 차이는 **통계적으로 유의**합니다 (적어도 한 집단은 다릅니다).")
        else:
            st.info(f"📌 p={p_val:.4f} ≥ 0.05 → 포지션군에 따른 평균 OPS 차이가 통계적으로 유의하다고 보기 어렵습니다.")
        st.caption("💡 일반적으로 내야 코너(1루수·3루수)나 외야 코너는 공격력 부담이 크고, 유격수·2루수·포수는 수비 부담이 커서 공격력이 상대적으로 낮게 나오는 경향이 있습니다 — 실제로 그런 패턴이 보이나요?")
    else:
        st.warning("일부 포지션군의 표본이 부족해 비교를 수행할 수 없습니다.")

# =================================================================
# ⚾ 투수 탭
# =================================================================
with tab_pitcher:
    render_glossary(["pit_ERA", "pit_WHIP", "pit_K9", "pit_BB9"])

    col_a, col_b = st.columns([1, 1.5])
    with col_a:
        p_year = st.selectbox("연도 선택 (팀별 비교에 사용)", options=years, index=len(years) - 1, key="p_year_corr")
    with col_b:
        p_min_ip = st.slider("최소 이닝(IP) 기준", min_value=0, max_value=180, value=30, step=10, key="p_min_ip_corr")

    p_base = df[(df["primary_position"] == "투수") & (df["pit_IP"] >= p_min_ip)].copy()
    st.caption(f"전체 기간 기준 분석 표본: **{len(p_base):,}개 투수-시즌 관측치** (IP≥{p_min_ip})")

    st.divider()
    st.subheader("1️⃣ 상관관계의 기초")

    p_pairs = {
        "ERA ↔ WHIP": ("pit_ERA", "pit_WHIP"),
        "ERA ↔ 탈삼진율(K9)": ("pit_ERA", "pit_K9"),
        "ERA ↔ 볼넷율(BB9)": ("pit_ERA", "pit_BB9"),
        "ERA ↔ 피안타율": ("pit_ERA", "pit_AVG"),
    }
    p_corr_rows = []
    for label, (a, c) in p_pairs.items():
        sub = p_base.dropna(subset=[a, c])
        if len(sub) >= 3:
            r, p = stats.pearsonr(sub[a], sub[c])
            p_corr_rows.append({"비교": label, "상관계수(r)": r, "p-value": p, "N": len(sub)})
    st.dataframe(
        pd.DataFrame(p_corr_rows), use_container_width=True, hide_index=True,
        column_config={
            "상관계수(r)": st.column_config.NumberColumn("상관계수(r)", format="%.3f"),
            "p-value": st.column_config.NumberColumn("p-value", format="%.4f"),
        },
    )

    p_pair_choice = st.selectbox("산점도로 확인할 조합 선택", options=list(p_pairs.keys()), key="p_pair")
    p_a, p_c = p_pairs[p_pair_choice]
    safe_scatter_with_trend(p_base, p_a, p_c, p_pair_choice.split(" ↔ ")[0], p_pair_choice.split(" ↔ ")[1], COLOR_SEQUENCE[2])

    st.markdown("""
**핵심 질문**
- 어떤 지표가 ERA와 가장 강한 상관관계를 보이나요?
- WHIP·피안타율은 ERA와 계산 구조가 밀접하게 얽혀있다는 점을 감안하면, 해석에 어떤 주의가 필요할까요?
""")

    st.divider()
    st.subheader(f"2️⃣ 팀별 투수력 비교 ({p_year}년, ERA는 낮을수록 우수)")

    p_team_season = p_base[(p_base["year"] == p_year)].dropna(subset=["pit_ERA"])
    if not p_team_season.empty:
        p_team_rows = []
        for t, g in p_team_season.groupby("team"):
            n = len(g)
            if n < 2:
                continue
            mean_v, sd_v = g["pit_ERA"].mean(), g["pit_ERA"].std()
            se_v = sd_v / np.sqrt(n)
            ci = stats.t.ppf(0.975, df=n - 1) * se_v
            p_team_rows.append({"team": t, "N": n, "평균": mean_v, "표준편차": sd_v, "ci": ci})
        p_team_stats = pd.DataFrame(p_team_rows).sort_values("평균", ascending=True).reset_index(drop=True)
        p_team_stats.insert(1, "순위", range(1, len(p_team_stats) + 1))

        st.dataframe(
            p_team_stats.drop(columns=["ci"]), use_container_width=True, hide_index=True,
            column_config={
                "team": st.column_config.TextColumn("구단"),
                "평균": st.column_config.NumberColumn("평균 ERA", format="%.2f"),
                "표준편차": st.column_config.NumberColumn("표준편차", format="%.2f"),
            },
        )
        gap = p_team_stats["평균"].max() - p_team_stats["평균"].min()
        st.metric(f"{p_year}년 팀별 평균 ERA 최대−최소 차이", f"{gap:.2f}",
                  help=f"최우수: {p_team_stats.iloc[0]['team']}, 최하위: {p_team_stats.iloc[-1]['team']}")
        mean_ci_dotplot(p_team_stats, "평균", "team", COLOR_SEQUENCE[2], ascending_is_better=False)
        st.caption("점 = 팀 평균 ERA, 가로선 = 95% 신뢰구간. (왼쪽일수록 ERA가 낮아 우수)")
    else:
        st.info("선택한 연도에 해당하는 데이터가 부족합니다.")

    st.divider()
    st.subheader("3️⃣ 시대별 투수력 비교 (2001–2009 / 2010–2019 / 2020–2025)")

    p_era_data = p_base.dropna(subset=["pit_ERA"]).copy()
    p_era_data["시대"] = p_era_data["year"].apply(to_era)

    p_era_rows = []
    for e in era_order:
        g = p_era_data[p_era_data["시대"] == e]["pit_ERA"]
        n = len(g)
        if n < 2:
            continue
        mean_v, sd_v = g.mean(), g.std()
        se_v = sd_v / np.sqrt(n)
        ci = stats.t.ppf(0.975, df=n - 1) * se_v
        p_era_rows.append({"시대": e, "N": n, "평균": mean_v, "표준편차": sd_v, "ci": ci})
    p_era_stats = pd.DataFrame(p_era_rows)
    st.dataframe(
        p_era_stats.drop(columns=["ci"]) if not p_era_stats.empty else p_era_stats,
        use_container_width=True, hide_index=True,
        column_config={
            "평균": st.column_config.NumberColumn("평균 ERA", format="%.2f"),
            "표준편차": st.column_config.NumberColumn("표준편차", format="%.2f"),
        },
    )
    if len(p_era_stats) == 3:
        mean_ci_dotplot(p_era_stats, "평균", "시대", COLOR_SEQUENCE[3], ascending_is_better=False)
        groups_p = [p_era_data[p_era_data["시대"] == e]["pit_ERA"] for e in era_order]
        f_stat, p_val = stats.f_oneway(*groups_p)
        m1, m2 = st.columns(2)
        m1.metric("ANOVA F-통계량", f"{f_stat:.3f}")
        m2.metric("p-value", f"{p_val:.4f}")
        if p_val < 0.05:
            st.success(f"📌 p={p_val:.4f} < 0.05 → 세 시대 간 평균 ERA 차이는 **통계적으로 유의**합니다.")
        else:
            st.info(f"📌 p={p_val:.4f} ≥ 0.05 → 세 시대 간 평균 ERA 차이가 통계적으로 유의하다고 보기 어렵습니다.")
    else:
        st.warning("일부 시대 구간의 표본이 부족해 비교를 수행할 수 없습니다.")
