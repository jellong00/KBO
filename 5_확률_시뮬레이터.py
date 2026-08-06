from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data import batting_data, load_data
from utils.ui import PLOTLY_CONFIG, modernize, setup_page

setup_page("KBO 확률 시뮬레이터")
df = load_data()
bat = batting_data(df, min_pa=50)

st.title("타자 가상 시즌 시뮬레이터")
st.caption("선택한 실제 선수-시즌의 타석 결과 비율을 이용해 동일한 타석 수의 가상 시즌을 반복 생성합니다.")

bat["label"] = (
    bat["player_name"].astype(str)
    + " | " + bat["year"].astype(str)
    + " | " + bat["team"].astype(str)
    + " | " + bat["hit_PA"].fillna(0).astype(int).astype(str) + " PA"
)
options = bat.sort_values(["year", "hit_OPS"], ascending=[False, False])
selected_label = st.selectbox("기준 선수-시즌", options["label"].tolist())
row = options.loc[options["label"] == selected_label].iloc[0]

c1, c2, c3 = st.columns(3)
with c1:
    target_pa = st.number_input("가상 시즌 타석", min_value=50, max_value=800, value=600, step=10)
with c2:
    simulations = st.number_input("반복 횟수", min_value=100, max_value=20000, value=3000, step=100)
with c3:
    seed = st.number_input("난수 시드", min_value=0, max_value=999999, value=42, step=1)

# Mutually exclusive plate-appearance outcomes. Sacrifice events are omitted and the residual becomes outs.
def safe_float(value: object, default: float = 0.0) -> float:
    return default if pd.isna(value) else float(value)

event_counts = {
    "1B": safe_float(row.get("hit_1B")),
    "2B": safe_float(row.get("hit_2B")),
    "3B": safe_float(row.get("hit_3B")),
    "HR": safe_float(row.get("hit_HR")),
    "BB": safe_float(row.get("hit_BB")),
    "HBP": safe_float(row.get("hit_HBP")),
}
observed_pa = max(safe_float(row.get("hit_PA")), 1.0)
used = sum(event_counts.values())
event_counts["OUT"] = max(observed_pa - used, 0.0)
labels = list(event_counts)
probabilities = np.array(list(event_counts.values()), dtype=float)
probabilities = probabilities / probabilities.sum()

rng = np.random.default_rng(int(seed))
draws = rng.multinomial(int(target_pa), probabilities, size=int(simulations))
sim = pd.DataFrame(draws, columns=labels)
sim["H"] = sim[["1B", "2B", "3B", "HR"]].sum(axis=1)
sim["AB"] = int(target_pa) - sim["BB"] - sim["HBP"]
sim["TB"] = sim["1B"] + 2 * sim["2B"] + 3 * sim["3B"] + 4 * sim["HR"]
sim["AVG"] = sim["H"] / sim["AB"].replace(0, np.nan)
sim["OBP"] = (sim["H"] + sim["BB"] + sim["HBP"]) / int(target_pa)
sim["SLG"] = sim["TB"] / sim["AB"].replace(0, np.nan)
sim["OPS"] = sim["OBP"] + sim["SLG"]

st.subheader("기준 기록")
m1, m2, m3, m4 = st.columns(4)
m1.metric("실제 타석", f"{observed_pa:,.0f}")
m2.metric("실제 홈런", f"{safe_float(row.get('hit_HR')):,.0f}")
m3.metric("실제 타율", f"{float(row.get('hit_AVG', np.nan)):.3f}" if pd.notna(row.get("hit_AVG")) else "-")
m4.metric("실제 OPS", f"{float(row.get('hit_OPS', np.nan)):.3f}" if pd.notna(row.get("hit_OPS")) else "-")

st.subheader("시뮬레이션 결과")
summary_metrics = ["HR", "H", "AVG", "OBP", "SLG", "OPS"]
summary = sim[summary_metrics].quantile([0.05, 0.5, 0.95]).T
summary.columns = ["5%", "중앙값", "95%"]
summary["평균"] = sim[summary_metrics].mean()
st.dataframe(summary[["평균", "5%", "중앙값", "95%"]].style.format("{:.3f}"), use_container_width=True)

left, right = st.columns(2)
with left:
    fig = px.histogram(sim, x="HR", nbins=35, marginal="box")
    modernize(fig, "가상 시즌 홈런 분포")
    fig.add_vline(x=sim["HR"].median(), line_dash="dash", annotation_text="중앙값")
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
with right:
    fig = px.scatter(sim.sample(min(1500, len(sim)), random_state=int(seed)), x="AVG", y="OPS", color="HR", opacity=0.55)
    modernize(fig, "타율-OPS 결과 분포")
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

threshold = st.slider("홈런 목표", min_value=0, max_value=max(60, int(sim["HR"].quantile(0.99)) + 5), value=min(30, max(0, int(sim["HR"].median()))))
prob = (sim["HR"] >= threshold).mean()
st.metric(f"{threshold}홈런 이상 달성 확률", f"{prob:.1%}")

with st.expander("모형 가정과 한계"):
    st.markdown(
        """
- 각 타석은 서로 독립이고 동일한 사건 확률을 가진다고 가정합니다.
- 단타·2루타·3루타·홈런·볼넷·사구·아웃만 사용합니다.
- 상대 투수, 구장, 타순, 부상, 연령, 수비, 시즌 환경 변화는 반영하지 않습니다.
- 따라서 결과는 확률 개념과 표본 변동성을 학습하기 위한 교육용 시뮬레이션이며, 공식 예측 모형이 아닙니다.
"""
    )
