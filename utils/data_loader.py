"""
data_loader.py
--------------
KBO.dta 파일을 로드하고, Stata 특유의 문자열 컬럼(타율/평균자책점/이닝 등)을
분석 가능한 숫자형으로 정제하는 공통 모듈.

이 데이터셋은 선수가 시즌 중 여러 포지션을 겸했을 경우, "동일한 타격 기록"이
포지션 개수만큼 행이 반복되어 저장되어 있다 (예: 좌익수/우익수를 겸하면 타격
기록이 완전히 같은 행이 2번 나타남). 이를 그대로 쓰면:
  - 순위/집계 차트에서 같은 선수가 여러 번 중복 표기되고 (구단분석 Top5 버그의 원인)
  - 백분위/코호트 계산이 중복 카운트로 왜곡된다.
따라서 load_data()는 "선수-시즌(-팀) 단위로 병합된" 테이블을 반환하고,
포지션별 수비 기록처럼 포지션 단위 세분화가 꼭 필요한 분석을 위해
load_position_level_data()를 별도로 제공한다.

이 모듈은 main.py 및 모든 pages/*.py에서 공통으로 import하여 사용합니다.
"""

import os
import pandas as pd
import streamlit as st

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "KBO.dta")

# 포지션 표기 순서 (야구 등번호 순서: 투수-포수-내야-외야)
POSITION_ORDER = ["투수", "포수", "1루수", "2루수", "3루수", "유격수", "좌익수", "중견수", "우익수"]


def _position_sort_key(pos):
    try:
        return POSITION_ORDER.index(pos)
    except ValueError:
        return len(POSITION_ORDER)


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


def _add_derived_metrics(df):
    """
    파생 지표 (세이버메트릭스 추정치) 계산.

    주의: 이 데이터셋에는 타자의 볼넷(BB), 사구(HBP) 컬럼이 별도로
    존재하지 않는다. 따라서 PA(타석) = AB + BB + HBP + SF + SAC 라는
    공식을 역산하여 BB+HBP를 다음과 같이 근사한다.
        BB_HBP_est = PA - AB - SF - SAC
    이 근사치를 바탕으로 OBP/OPS/wOBA를 "추정"하며, 실제값과 다소
    차이가 있을 수 있음을 대시보드 상에 명시한다.
    """
    if all(c in df.columns for c in ["hit_PA", "hit_AB", "hit_SF", "hit_SAC", "hit_H",
                                       "hit_2B", "hit_3B", "hit_HR", "hit_TB"]):
        bb_hbp_est = (df["hit_PA"] - df["hit_AB"] - df["hit_SF"].fillna(0) - df["hit_SAC"].fillna(0))
        bb_hbp_est = bb_hbp_est.clip(lower=0)
        df["hit_BB_HBP_est"] = bb_hbp_est

        # 출루율 추정치 (OBP) = (안타 + 볼넷/사구 추정치) / (타수 + 볼넷/사구 추정치 + 희생플라이)
        denom_obp = df["hit_AB"] + bb_hbp_est + df["hit_SF"].fillna(0)
        df["hit_OBP_est"] = ((df["hit_H"] + bb_hbp_est) / denom_obp).where(denom_obp > 0)

        # 장타율 (SLG) = 총루타 / 타수 (확정값)
        df["hit_SLG"] = (df["hit_TB"] / df["hit_AB"]).where(df["hit_AB"] > 0)

        # OPS(추정) = 출루율(추정) + 장타율
        df["hit_OPS_est"] = df["hit_OBP_est"] + df["hit_SLG"]

        # 1루타 = 안타 - 2루타 - 3루타 - 홈런
        df["hit_1B"] = df["hit_H"] - df["hit_2B"].fillna(0) - df["hit_3B"].fillna(0) - df["hit_HR"].fillna(0)

        # wOBA(추정): 2020년대 표준 선형가중치의 근사 평균값 사용 (볼넷/사구 미분리로 단일 가중치 0.72 적용)
        woba_num = (
            0.72 * bb_hbp_est
            + 0.89 * df["hit_1B"]
            + 1.27 * df["hit_2B"].fillna(0)
            + 1.62 * df["hit_3B"].fillna(0)
            + 2.10 * df["hit_HR"].fillna(0)
        )
        df["hit_wOBA_est"] = (woba_num / df["hit_PA"]).where(df["hit_PA"] > 0)

    # ---- 투수 파생지표 ----
    # K/9 = 탈삼진 / 이닝 * 9 (9이닝당 탈삼진 개수, 높을수록 좋음)
    if all(c in df.columns for c in ["pit_SO", "pit_IP"]):
        df["pit_K9"] = (df["pit_SO"] / df["pit_IP"] * 9).where(df["pit_IP"] > 0)
    # BB/9 = 볼넷 / 이닝 * 9 (9이닝당 허용 볼넷, 낮을수록 좋음)
    if all(c in df.columns for c in ["pit_BB", "pit_IP"]):
        df["pit_BB9"] = (df["pit_BB"] / df["pit_IP"] * 9).where(df["pit_IP"] > 0)
    # HR/9 = 피홈런 / 이닝 * 9 (9이닝당 허용 홈런, 낮을수록 좋음)
    if all(c in df.columns for c in ["pit_HR", "pit_IP"]):
        df["pit_HR9"] = (df["pit_HR"] / df["pit_IP"] * 9).where(df["pit_IP"] > 0)

    return df


@st.cache_data(show_spinner="KBO 데이터를 불러오는 중입니다...")
def load_position_level_data():
    """
    KBO.dta를 로드하고 정제한, '포지션 단위' 원본 그래뉼래러티 데이터.
    한 선수가 시즌 중 여러 포지션을 뛰었으면 여러 행으로 남아있다.
    포지션별 수비 기록(FPCT 등) 분석처럼 포지션 단위 구분이 꼭 필요한 경우에만 사용.
    """
    df = pd.read_stata(DATA_PATH)

    # ---- 문자열로 저장된 숫자 컬럼 정제 ----
    string_numeric_cols = ["hit_AVG", "pit_ERA", "pit_WPCT", "def_FPCT", "def_CS_pct"]
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

    df = _add_derived_metrics(df)
    return df


def _combine_positions(pos_series):
    """포지션 목록을 표준 순서(투수-포수-내야-외야)로 정렬해 '/'로 합친다."""
    vals = [p for p in pos_series if isinstance(p, str) and p.strip() not in ("", "nan")]
    uniq = sorted(set(vals), key=_position_sort_key)
    return "/".join(uniq) if uniq else ""


@st.cache_data(show_spinner="선수-시즌 단위로 기록을 병합하는 중입니다...")
def load_data():
    """
    선수-시즌(-팀) 단위로 병합된 '대표' 테이블.
    한 선수가 여러 포지션을 겸해 발생하는 완전 동일 기록의 중복 행을
    하나로 합치고, def_POS 컬럼에 겸한 포지션을 '좌익수/우익수'처럼 표기한다.
    대시보드의 거의 모든 순위/집계/비교 분석은 이 함수를 사용해야 한다.
    """
    raw = load_position_level_data()

    hit_cols = [c for c in raw.columns if c.startswith("hit_")]
    identity_cols = ["player_id", "player_name", "year", "team"] + hit_cols
    other_cols = [c for c in raw.columns if c not in identity_cols + ["def_POS"]]

    agg_dict = {c: "first" for c in other_cols}
    agg_dict["def_POS"] = _combine_positions

    merged = raw.groupby(identity_cols, dropna=False).agg(agg_dict).reset_index()
    return merged


def get_years(df):
    return sorted(df["year"].dropna().unique().tolist())


def get_teams(df):
    return sorted([t for t in df["team"].dropna().unique().tolist() if t and t != "nan"])


def get_positions(df):
    """데이터에 존재하는 포지션들을 표준 순서로 정렬해 반환 (빈 값 제외)."""
    all_pos = set()
    for s in df["def_POS"].dropna():
        for p in str(s).split("/"):
            if p and p != "nan":
                all_pos.add(p)
    return sorted(all_pos, key=_position_sort_key)
