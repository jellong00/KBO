"""
glossary.py
-----------
대시보드 전반에서 사용하는 야구 지표 약어에 대한 한글 설명 모음.
- 코드 내 주석뿐 아니라, 화면에도 "지표 설명" expander/help 텍스트로 노출한다.
"""

import streamlit as st

# key: 컬럼명 또는 축약어, value: (한글 표시명, 설명)
STAT_GLOSSARY = {
    # 타자 지표
    "hit_AVG": ("타율 (AVG)", "안타 수 / 타수. 타석에서 안타를 칠 확률."),
    "hit_OBP_est": ("출루율 (OBP, 추정)", "타석에서 출루(안타+볼넷+사구)한 비율. 이 데이터셋엔 볼넷 컬럼이 없어 PA-AB-SF-SAC 로 추정."),
    "hit_SLG": ("장타율 (SLG)", "타수당 총 루타(단타1루, 2루타2루, 3루타3루, 홈런4루)의 평균."),
    "hit_OPS_est": ("OPS (추정)", "출루율 + 장타율. 타자의 전반적인 공격력을 요약하는 대표 지표."),
    "hit_wOBA_est": ("wOBA (추정)", "가중출루율. 단타/2루타/3루타/홈런/볼넷에 실제 득점 기여도만큼 가중치를 달리 부여한 종합 공격 지표."),
    "hit_HR": ("홈런 (HR)", "시즌 홈런 개수."),
    "hit_RBI": ("타점 (RBI)", "타자가 쳐서 불러들인 주자 수."),
    "hit_PA": ("타석 (PA)", "타자가 타석에 들어선 횟수 (규정 타석 충족 여부 판단 기준)."),
    # 투수 지표
    "pit_ERA": ("평균자책점 (ERA)", "9이닝당 투수 책임으로 낸 자책점. 낮을수록 우수."),
    "pit_WHIP": ("WHIP", "이닝당 허용한 안타+볼넷 수 (Walks+Hits per Inning Pitched). 낮을수록 제구/억제력이 좋음."),
    "pit_IP": ("이닝 (IP)", "투수가 던진 이닝 수 (규정 이닝 충족 여부 판단 기준)."),
    "pit_K9": ("탈삼진율 (K/9)", "9이닝당 탈삼진 개수. 높을수록 탈삼진 능력이 뛰어남."),
    "pit_BB9": ("볼넷율 (BB/9)", "9이닝당 허용 볼넷 개수. 낮을수록 제구가 좋음."),
    "pit_HR9": ("피홈런율 (HR/9)", "9이닝당 허용 홈런 개수. 낮을수록 장타 억제력이 좋음."),
    "pit_SO": ("탈삼진 (SO)", "시즌 탈삼진 총 개수."),
    "pit_BB": ("볼넷 (BB)", "투수가 허용한 볼넷 총 개수."),
    "pit_W": ("승 (W)", "시즌 승리 수."),
    "pit_SV": ("세이브 (SV)", "시즌 세이브 수."),
    "pit_HLD": ("홀드 (HLD)", "시즌 홀드 수."),
    # 수비/주루 지표
    "def_FPCT": ("수비율 (FPCT)", "(자살+보살) / (자살+보살+실책). 수비 성공률."),
    "run_SBA": ("도루 시도 (SBA)", "시즌 도루 시도 횟수."),
    "run_SB_pct": ("도루 성공률", "도루 성공 / 도루 시도 (%)."),
    "run_OOB": ("주루사 (OOB)", "도루 외 상황에서 주루 실패로 아웃된 횟수."),
}


def render_glossary(keys, title="📖 지표 설명", expanded=False):
    """주어진 컬럼키 목록에 대한 설명을 expander로 렌더링."""
    rows = [(STAT_GLOSSARY[k][0], STAT_GLOSSARY[k][1]) for k in keys if k in STAT_GLOSSARY]
    if not rows:
        return
    with st.expander(title, expanded=expanded):
        for label, desc in rows:
            st.markdown(f"- **{label}**: {desc}")
