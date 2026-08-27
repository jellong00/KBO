import streamlit as st
import pandas as pd

from utils.data_cleaner import get_full_panel
from utils.variables import VARIABLES

st.set_page_config(
    page_title="공공기관 계량분석 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 공공기관 계량분석 대시보드")
st.markdown("##### 실제 공공기관 데이터로 질문을 만들고, 분포를 확인하고, 관계를 탐색하는 기초계량분석 실습 대시보드")
st.divider()

with st.spinner("데이터를 불러오는 중입니다..."):
    panel = get_full_panel()

used_cols = {v["column"] for v in VARIABLES.values() if v["column"] in panel.columns}

m1, m2, m3, m4 = st.columns(4)
m1.metric("분석기관 수", f"{panel['기관명'].nunique():,}개")
m2.metric("연도 범위", f"{panel['연도'].min()}–{panel['연도'].max()}")
m3.metric("기관-연도 관측치", f"{panel.shape[0]:,}건")
m4.metric("결합된 변수 수", f"{len(used_cols):,}개")

st.divider()

# ---------------- 실데이터 기반 흥미유도 질문 ----------------
st.markdown("### 🤔 이 데이터로 답할 수 있는 질문들")

latest_year = panel["연도"].max()
earliest_year = panel["연도"].min()
snap = panel[panel["연도"] == latest_year]


def safe_ratio_top():
    if "기관장직원보수배율" in snap.columns:
        s = snap[["기관명", "기관장직원보수배율"]].dropna()
        if not s.empty:
            row = s.loc[s["기관장직원보수배율"].idxmax()]
            return row["기관명"], row["기관장직원보수배율"]
    return None, None


def safe_gov_compare():
    if "정부지원수입" in snap.columns and "정부지원의존도" in snap.columns:
        s1 = snap[["기관명", "정부지원수입"]].dropna()
        s2 = snap[["기관명", "정부지원의존도"]].dropna()
        if not s1.empty and not s2.empty:
            top_amt = s1.loc[s1["정부지원수입"].idxmax(), "기관명"]
            top_ratio = s2.loc[s2["정부지원의존도"].idxmax(), "기관명"]
            return top_amt, top_ratio
    return None, None


def safe_female_leave_by_type():
    if "여성육아휴직사용자수" in panel.columns:
        s = panel.groupby("기관유형")["여성육아휴직사용자수"].mean().dropna()
        if not s.empty:
            return s.idxmax(), s.max()
    return None, None


def safe_salary_growth_top():
    col = "직원평균보수"
    if col in panel.columns:
        first = panel[panel["연도"] == earliest_year][["기관명", col]].dropna().rename(columns={col: "초기값"})
        last = panel[panel["연도"] == latest_year][["기관명", col]].dropna().rename(columns={col: "최근값"})
        merged = pd.merge(first, last, on="기관명")
        merged = merged[merged["초기값"] > 0]
        if not merged.empty:
            merged["증가율"] = (merged["최근값"] - merged["초기값"]) / merged["초기값"] * 100
            row = merged.loc[merged["증가율"].idxmax()]
            return row["기관명"], row["증가율"]
    return None, None


q_org, q_ratio = safe_ratio_top()
q_amt_org, q_ratio_org = safe_gov_compare()
q_type, q_type_rate = safe_female_leave_by_type()
q_growth_org, q_growth_rate = safe_salary_growth_top()

qc1, qc2 = st.columns(2)
qc3, qc4 = st.columns(2)

with qc1:
    if q_org:
        st.info(f"💰 **기관장 연봉이 직원 평균보수의 몇 배?** — {latest_year}년 기준 **{q_org}**이(가) "
                f"**{q_ratio:.1f}배**로 가장 높습니다.")
    else:
        st.info("💰 기관장 연봉은 직원 평균보수의 몇 배일까요? — [보수·복리후생·채용] 페이지에서 확인해보세요.")
with qc2:
    if q_amt_org and q_ratio_org:
        same = "같습니다" if q_amt_org == q_ratio_org else "다릅니다"
        st.info(f"🏛️ **정부지원수입 최다 기관과 정부지원의존도 최고 기관은 같을까?** — {same}. "
                f"(수입 최다: {q_amt_org} / 의존도 최고: {q_ratio_org})")
    else:
        st.info("🏛️ 정부지원수입이 많은 기관과 정부지원의존도가 높은 기관은 같을까요?")
with qc3:
    if q_type:
        st.info(f"👶 **여성 육아휴직 사용자 수가 가장 많은 기관유형은?** — **{q_type}** (평균 {q_type_rate:.1f}명)")
    else:
        st.info("👶 육아휴직 사용자 수가 많은 기관유형은 어디일까요?")
with qc4:
    if q_growth_org:
        st.info(f"📈 **{earliest_year}~{latest_year}년, 평균보수가 가장 많이 오른 기관은?** — "
                f"**{q_growth_org}** (+{q_growth_rate:.1f}%)")
    else:
        st.info("📈 최근 기간 평균보수가 가장 많이 상승한 기관은 어디일까요?")

st.caption("💡 더 자세한 답은 좌측 사이드바의 각 분석 페이지에서 직접 탐색해보세요.")

st.divider()

# ---------------- 계량분석 핵심개념 ----------------
st.markdown("### 📚 이 대시보드를 보기 전에: 계량분석 핵심개념")
c1, c2, c3, c4 = st.columns(4)
c5, c6, c7 = st.columns(3)

with c1:
    st.markdown("#### ① 평균과 중앙값")
    st.caption("평균만으로 전체 분포를 설명할 수 있을까요? 극단값이 있으면 평균과 중앙값이 크게 달라집니다.")
with c2:
    st.markdown("#### ② 분포와 이상치")
    st.caption("극단값(이상치)은 평균뿐 아니라 회귀분석 결과에도 큰 영향을 줄 수 있습니다.")
with c3:
    st.markdown("#### ③ 총액과 비율")
    st.caption("기관 규모가 다른데 총액을 그대로 비교해도 될까요? '1인당' 지표가 필요한 이유입니다.")
with c4:
    st.markdown("#### ④ 집단 차이")
    st.caption("기관유형별 평균 차이가 통계적으로 유의하다고 해서 그것이 곧 원인은 아닙니다.")
with c5:
    st.markdown("#### ⑤ 상관관계")
    st.caption("두 변수가 함께 움직인다고 해서 인과관계라고 할 수 있을까요?")
with c6:
    st.markdown("#### ⑥ 통제변수")
    st.caption("다른 조건(기관유형, 규모 등)을 고려하면 관계가 어떻게 달라질까요?")
with c7:
    st.markdown("#### ⑦ 시간 변화")
    st.caption("기관 간의 차이와 동일 기관의 시간에 따른 변화는 같은 정보를 담고 있을까요?")

st.divider()

st.markdown("### 페이지 안내")
st.caption("페이지는 4개 섹션으로 묶여 있습니다. 모든 페이지를 매번 쓸 필요는 없고, 필요한 페이지만 골라 쓰는 '분석 모듈'이라고 보면 됩니다.")

st.markdown("""
**I. 데이터 이해**
1. 기술통계 및 변수분포 — 선택한 변수는 어떤 분포를 갖는가? (일·가정양립 지표도 여기서 카테고리로 탐색 가능)
2. 기관유형별 비교 — 기관유형에 따라 평균·분포가 다른가?
3. 주무부처별 비교 — 주무부처별 산하기관은 어떻게 다른가? (기관유형×주무부처 교차분석 포함)

**II. 공공기관 주요 지표**
4. 수입·지출 구조 — 기관별 재정규모와 수입구성은 어떻게 다른가?
5. 법인세 분석 — 과세표준·결정세액은 어떻게 분포하고 연관되는가?
6. 보수 및 복리후생 — 보수와 복리후생 수준은 기관별로 어떻게 다른가?
7. 채용 및 인력구성 — 채용규모와 채용률·성별구성은 어떻게 다른가?

**III. 탐색적 계량분석**
8. 두 변수 관계분석 — 두 지표는 얼마나 함께 움직이는가?
9. 집단별 관계 및 상관구조 — 전체 관계가 유형·부처 내부에서도 같은가? (부문간 관계 지도 포함)
10. 기관 프로필 — 특정 기관은 전체·유형·부처에서 어디쯤인가?
11. 연도별 수준 변화 — 지표 수준은 시간에 따라 어떻게 변했는가?
12. 변화율 분석 — 어떤 기관의 변화가 크며, 순위는 안정적인가?

**IV. 심화 계량분석**
13. 다중회귀분석 — 통제 후에도 관계가 유지되는가?
14. 패널데이터 분석 — 기관 간 차이와 기관 내부 변화는 어떻게 다른가?
""")

st.divider()
st.caption(
    "좌측 사이드바 **Pages** 메뉴에서 각 분석 페이지로 이동하세요. "
    "모든 페이지의 필터(연도·기관유형·주무부처·기관명)는 종속적으로 연동됩니다."
)
