"""
utils/data_loader.py
----------------------
데이터 로딩 + 캐싱 + 파생변수 계산을 담당.

- load_data(): 선수-시즌 단위(중복 제거 완료)의 메인 데이터
- get_years / get_teams / get_positions: 필터 옵션 헬퍼

주의:
- 원본 KBO.dta는 선수가 한 시즌에 여러 포지션을 겸하면 포지션별로 행이 나뉘어 있었음.
  data/kbo_clean.parquet 은 이미 이 문제를 해결해서 "선수-시즌 1행" 구조로 병합해둔 파일.
  (병합 로직: clean_data.py 참고 - 수비 카운팅 스탯은 합산, 타/투/주루 스탯은 원래 동일값이라 그대로 사용)
- positions_played 컬럼에 그 시즌에 뛴 모든 포지션이 ", "로 구분되어 들어있음.
  primary_position 컬럼은 그 중 가장 많이 뛴(수비이닝 기준) 포지션 하나.
"""

import streamlit as st
import pandas as pd

CLEAN_DATA_PATH = "data/kbo_clean.dta"


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_stata(CLEAN_DATA_PATH)

    # 9이닝당 피홈런 (원본엔 없어서 직접 계산; K9/BB9는 클리닝 단계에서 이미 계산되어 들어있음)
    df["pit_HR9"] = (df["pit_HR"] / df["pit_IP"] * 9).where(df["pit_IP"] > 0)

    return df



def get_years(df: pd.DataFrame) -> list:
    return sorted(df["year"].dropna().unique().astype(int).tolist())


def get_teams(df: pd.DataFrame) -> list:
    return sorted(df["team"].dropna().unique().tolist())


def get_positions(df: pd.DataFrame) -> list:
    """primary_position 기준 고유 포지션 목록 (투수 포함, 빈 값 제외)"""
    pos = df["primary_position"].dropna()
    pos = pos[pos.str.strip() != ""]
    return sorted(pos.unique().tolist())
