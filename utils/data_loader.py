"""
data_loader.py
--------------
KBO.dta 파일을 로드하고, Stata 특유의 문자열 컬럼(타율/평균자책점/이닝 등)을
분석 가능한 숫자형으로 정제하는 공통 모듈.

이 모듈은 main.py 및 모든 pages/*.py에서 공통으로 import하여 사용합니다.
"""

import os
import re
import pandas as pd
import streamlit as st

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "KBO.dta")


def _innings_to_float(value):
    """
    KBO 이닝(IP) 표기는 '4 2/3', '159 2/3' 처럼 분수가 섞인 문자열로 저장되어 있음.
    이를 실제 아웃카운트 기준 소수(예: 4 2/3 -> 4.667)로 변환한다.
    '-' 또는 빈 문자열은 결측치(NaN)로 처리한다.
    """
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s in ("", "-", "nan"):
        return None
    if " " in s:
        whole, frac = s.split(" ", 1)
        try:
            whole = float(whole)
            num, den = frac.split("/")
            return whole + float(num) / float(den)
        except Exception:
            return None
    try:
        return float(s)
    except Exception:
        return None


def _clean_numeric_string(value):
    """
    타율(hit_AVG), 평균자책점(pit_ERA), 승률(pit_WPCT), 수비율(def_FPCT),
    도루저지율(def_CS_pct) 등 문자열로 저장된 숫자 컬럼을 float으로 변환.
    '-' 또는 빈 문자열은 결측치로 처리.
    """
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s in ("", "-", "nan"):
        return None
    try:
        return float(s)
    except Exception:
        return None


@st.cache_data(show_spinner="KBO 데이터를 불러오는 중입니다...")
def load_data():
    """
    KBO.dta를 로드하고 파생 지표를 계산하여 반환한다.
    - data/KBO.dta 경로에 파일이 있어야 함 (리포지토리 루트 기준)
    """
    df = pd.read_stata(DATA_PATH)

    # ---- 문자열로 저장된 숫자 컬럼 정제 ----
    string_numeric_cols = [
        "hit_AVG", "pit_ERA", "pit_WPCT", "def_FPCT", "def_CS_pct",
    ]
    for col in string_numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(_clean_numeric_string)

    # ---- 이닝(분수 표기) 컬럼 정제 ----
    for col in ["pit_IP", "def_IP"]:
        if col in df.columns:
            df[col] = df[col].apply(_innings_to_float)

    # ---- 선수명/팀명 공백 제거 ----
    for col in ["player_name", "team", "def_POS"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # ================================================================
    # 파생 지표 (세이버메트릭스 추정치)
    #
    # 주의: 이 데이터셋에는 타자의 볼넷(BB), 사구(HBP) 컬럼이 별도로
    # 존재하지 않는다. 따라서 PA(타석) = AB + BB + HBP + SF + SAC 라는
    # 공식을 역산하여 BB+HBP를 다음과 같이 근사한다.
    #     BB_HBP_est = PA - AB - SF - SAC
    # 이 근사치를 바탕으로 OBP/OPS/wOBA를 "추정"하며, 실제값과 다소
    # 차이가 있을 수 있음을 대시보드 상에 명시한다.
    # ================================================================
    if all(c in df.columns for c in ["hit_PA", "hit_AB", "hit_SF", "hit_SAC", "hit_H",
                                       "hit_2B", "hit_3B", "hit_HR", "hit_TB"]):
        bb_hbp_est = (df["hit_PA"] - df["hit_AB"] - df["hit_SF"].fillna(0) - df["hit_SAC"].fillna(0))
        bb_hbp_est = bb_hbp_est.clip(lower=0)
        df["hit_BB_HBP_est"] = bb_hbp_est

        # 출루율 추정치 (OBP)
        denom_obp = df["hit_AB"] + bb_hbp_est + df["hit_SF"].fillna(0)
        df["hit_OBP_est"] = ((df["hit_H"] + bb_hbp_est) / denom_obp).where(denom_obp > 0)

        # 장타율 (SLG) - TB/AB는 확정값
        df["hit_SLG"] = (df["hit_TB"] / df["hit_AB"]).where(df["hit_AB"] > 0)

        # OPS 추정치
        df["hit_OPS_est"] = df["hit_OBP_est"] + df["hit_SLG"]

        # 1루타
        df["hit_1B"] = df["hit_H"] - df["hit_2B"].fillna(0) - df["hit_3B"].fillna(0) - df["hit_HR"].fillna(0)

        # wOBA 추정치 (2020년대 표준 계수의 근사 평균값 사용, BB/HBP 미분리로 단일 가중치 0.72 적용)
        woba_num = (
            0.72 * bb_hbp_est
            + 0.89 * df["hit_1B"]
            + 1.27 * df["hit_2B"].fillna(0)
            + 1.62 * df["hit_3B"].fillna(0)
            + 2.10 * df["hit_HR"].fillna(0)
        )
        df["hit_wOBA_est"] = (woba_num / df["hit_PA"]).where(df["hit_PA"] > 0)

    # ---- 투수 파생지표 ----
    if all(c in df.columns for c in ["pit_SO", "pit_IP"]):
        df["pit_K9"] = (df["pit_SO"] / df["pit_IP"] * 9).where(df["pit_IP"] > 0)
    if all(c in df.columns for c in ["pit_BB", "pit_IP"]):
        df["pit_BB9"] = (df["pit_BB"] / df["pit_IP"] * 9).where(df["pit_IP"] > 0)
    if all(c in df.columns for c in ["pit_HR", "pit_IP"]):
        df["pit_HR9"] = (df["pit_HR"] / df["pit_IP"] * 9).where(df["pit_IP"] > 0)

    return df


def get_years(df):
    return sorted(df["year"].dropna().unique().tolist())


def get_teams(df):
    return sorted([t for t in df["team"].dropna().unique().tolist() if t and t != "nan"])
