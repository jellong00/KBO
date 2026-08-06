"""
data_loader.py
--------------
KBO.dta 파일을 로드하고, Stata 특유의 문자열 컬럼(타율/평균자책점/이닝 등)을
분석 가능한 숫자형으로 정제하는 공통 모듈.

[2024-업데이트 데이터셋 기준]
새 데이터셋은 예전보다 훨씬 풍부하다:
  - 2001년 시즌: 타자 볼넷(hit_BB)/사구(hit_HBP)/삼진(hit_SO) 등 세부기록 존재
  - 2002~2025년 시즌: 출루율/장타율/OPS(hit_OBP, hit_SLG, hit_OPS)가 이미 계산되어 제공됨
  - 득점권 타율(hit_RISP), 대타 타율(hit_PH_BA), 땅볼/뜬공비율(pit_GO_AO),
    BABIP(pit_BABIP), 세이브기회(pit_SVO), 선발/구원 승수(pit_Wgs/pit_Wgr) 등 다수 신규 지표 추가
따라서 OBP/SLG/OPS/wOBA는 아래 우선순위로 계산한다:
  1) 데이터에 이미 제공된 값(hit_OBP/hit_SLG/hit_OPS)이 있으면 그대로 사용 (가장 정확)
  2) 없지만 실제 볼넷/사구(hit_BB, hit_HBP)가 있으면 그 값으로 직접 계산 (2001년)
  3) 그마저 없으면, 제공된 출루율로 볼넷+사구를 역산하거나(가능한 경우) PA 기반 근사치 사용

이 데이터셋은 선수가 시즌 중 여러 포지션을 겸했을 경우, "동일한 기록"이 포지션 개수만큼
반복된 행으로 저장되어 있다. 이를 그대로 쓰면 순위/집계가 중복 카운트되므로,
load_data()는 "선수-시즌(-팀) 단위로 병합된" 테이블을 반환하고, 포지션별 수비 기록처럼
포지션 단위 세분화가 꼭 필요한 분석을 위해 load_position_level_data()를 별도로 제공한다.

이 모듈은 main.py 및 모든 pages/*.py에서 공통으로 import하여 사용합니다.
"""

import os
import pandas as pd
import numpy as np
import streamlit as st

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "KBO.dta")

# 포지션 표기 순서 (야구 등번호 순서: 투수-포수-내야-외야)
POSITION_ORDER = ["투수", "포수", "1루수", "2루수", "3루수", "유격수", "좌익수", "중견수", "우익수"]

# 소수점 문자열로 저장된 "단순 숫자" 컬럼 ('-'/''는 결측치로 처리)
SIMPLE_NUMERIC_STRING_COLS = [
    "hit_AVG", "pit_ERA", "pit_WPCT", "def_FPCT", "def_CS_pct", "pit_GO_AO", "pit_P_IP", "pit_SLG",
]
# 이닝 표기('4 2/3')처럼 분수가 섞인 컬럼
FRACTION_STRING_COLS = ["pit_IP", "def_IP"]


def _position_sort_key(pos):
    try:
        return POSITION_ORDER.index(pos)
    except ValueError:
        return len(POSITION_ORDER)


def _innings_to_float(value):
    """'4 2/3' 같은 이닝 표기를 4.667 같은 소수로 변환. '-'/빈문자열은 NaN."""
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
    """'-'/빈 문자열이 섞인 숫자 문자열 컬럼을 float으로 변환."""
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
    파생 지표 계산. 실제 제공된 값을 최우선으로 사용하고, 없을 때만 추정치로 보완한다.
    (컬럼명은 이전 버전과의 호환을 위해 hit_OBP_est / hit_OPS_est / hit_wOBA_est 등을 그대로 유지하되,
     이제는 대부분 '추정'이 아니라 실제 제공값으로 채워진다.)
    """
    has_cols = lambda cols: all(c in df.columns for c in cols)

    if has_cols(["hit_PA", "hit_AB", "hit_SF", "hit_SAC", "hit_H", "hit_2B", "hit_3B", "hit_HR", "hit_TB"]):
        ab = df["hit_AB"]
        sf = df["hit_SF"].fillna(0)
        sac = df["hit_SAC"].fillna(0)
        h = df["hit_H"]
        pa = df["hit_PA"]

        # ---- 볼넷+사구(BB+HBP) 추정: 실제값 > 역산값 > PA기반 근사 순으로 사용 ----
        has_real_bb = "hit_BB" in df.columns and "hit_HBP" in df.columns
        real_bb_hbp = (df["hit_BB"].fillna(0) + df["hit_HBP"].fillna(0)) if has_real_bb else pd.Series(np.nan, index=df.index)
        real_bb_mask = (df["hit_BB"].notna() & df["hit_HBP"].notna()) if has_real_bb else pd.Series(False, index=df.index)

        if "hit_OBP" in df.columns:
            # OBP = (H + BB+HBP) / (AB + BB+HBP + SF)  =>  BB+HBP = (OBP*(AB+SF) - H) / (1 - OBP)
            obp_given = df["hit_OBP"]
            denom = (1 - obp_given)
            reverse_bb_hbp = ((obp_given * (ab + sf) - h) / denom).where(denom > 0)
            reverse_bb_hbp = reverse_bb_hbp.clip(lower=0)
        else:
            reverse_bb_hbp = pd.Series(np.nan, index=df.index)

        approx_bb_hbp = (pa - ab - sf - sac).clip(lower=0)

        bb_hbp = real_bb_hbp.where(real_bb_mask)
        bb_hbp = bb_hbp.fillna(reverse_bb_hbp)
        bb_hbp = bb_hbp.fillna(approx_bb_hbp)
        df["hit_BB_HBP_est"] = bb_hbp

        # ---- 출루율: 제공값 우선, 없으면 위 bb_hbp로 직접 계산 ----
        denom_obp = ab + bb_hbp + sf
        computed_obp = ((h + bb_hbp) / denom_obp).where(denom_obp > 0)
        df["hit_OBP_est"] = df["hit_OBP"].fillna(computed_obp) if "hit_OBP" in df.columns else computed_obp

        # ---- 장타율: 제공값 우선, 없으면 TB/AB ----
        computed_slg = (df["hit_TB"] / ab).where(ab > 0)
        df["hit_SLG"] = df["hit_SLG"].fillna(computed_slg) if "hit_SLG" in df.columns else computed_slg

        # ---- OPS: 제공값 우선, 없으면 OBP+SLG ----
        computed_ops = df["hit_OBP_est"] + df["hit_SLG"]
        df["hit_OPS_est"] = df["hit_OPS"].fillna(computed_ops) if "hit_OPS" in df.columns else computed_ops

        # 1루타
        df["hit_1B"] = h - df["hit_2B"].fillna(0) - df["hit_3B"].fillna(0) - df["hit_HR"].fillna(0)

        # wOBA(추정): 표준 선형가중치의 근사 평균값 사용 (bb_hbp는 위에서 계산한 최선의 값 사용)
        woba_num = (
            0.72 * bb_hbp
            + 0.89 * df["hit_1B"]
            + 1.27 * df["hit_2B"].fillna(0)
            + 1.62 * df["hit_3B"].fillna(0)
            + 2.10 * df["hit_HR"].fillna(0)
        )
        df["hit_wOBA_est"] = (woba_num / pa).where(pa > 0)

    # ---- 투수 파생지표: 제공값(pit_K_9/pit_BB_9) 우선, 없으면 직접 계산 ----
    if has_cols(["pit_SO", "pit_IP"]):
        computed_k9 = (df["pit_SO"] / df["pit_IP"] * 9).where(df["pit_IP"] > 0)
        df["pit_K9"] = df["pit_K_9"].fillna(computed_k9) if "pit_K_9" in df.columns else computed_k9
    if has_cols(["pit_BB", "pit_IP"]):
        computed_bb9 = (df["pit_BB"] / df["pit_IP"] * 9).where(df["pit_IP"] > 0)
        df["pit_BB9"] = df["pit_BB_9"].fillna(computed_bb9) if "pit_BB_9" in df.columns else computed_bb9
    if has_cols(["pit_HR", "pit_IP"]):
        df["pit_HR9"] = (df["pit_HR"] / df["pit_IP"] * 9).where(df["pit_IP"] > 0)

    return df


@st.cache_data(show_spinner="KBO 데이터를 불러오는 중입니다...")
def load_position_level_data():
    """
    KBO.dta를 로드하고 정제한, '포지션 단위' 원본 그래뉼래러티 데이터.
    한 선수가 시즌 중 여러 포지션을 뛰었으면 여러 행으로 남아있다.
    포지션별 수비 기록(FPCT 등) 분석처럼 포지션 단위 구분이 꼭 필요한 경우에만 사용.
    """
    if not os.path.exists(DATA_PATH):
        # 배포 환경(Streamlit Cloud 등)에서 data/KBO.dta가 리포지토리에 커밋되지 않았거나
        # 경로가 어긋난 경우 원인 파악이 쉽도록 상세 정보를 함께 보여준다.
        repo_root = os.path.dirname(os.path.dirname(__file__))
        try:
            root_listing = os.listdir(repo_root)
        except Exception:
            root_listing = ["(리포지토리 루트를 읽을 수 없음)"]
        data_dir = os.path.join(repo_root, "data")
        try:
            data_listing = os.listdir(data_dir) if os.path.isdir(data_dir) else ["(data 폴더 자체가 없음)"]
        except Exception:
            data_listing = ["(data 폴더를 읽을 수 없음)"]

        st.error(
            "❌ 데이터 파일을 찾을 수 없습니다.\n\n"
            f"찾으려던 경로: `{DATA_PATH}`\n\n"
            f"리포지토리 루트({repo_root})의 파일 목록:\n{root_listing}\n\n"
            f"data 폴더 내용:\n{data_listing}\n\n"
            "**확인해보세요:**\n"
            "1. GitHub 리포지토리에 `data/KBO.dta` 파일이 실제로 커밋/푸시되었는지 "
            "(GitHub 웹사이트에서 리포지토리를 열어 `data` 폴더와 그 안의 `KBO.dta`가 보이는지 확인)\n"
            "2. `.gitignore`에 `data/`나 `*.dta`가 포함되어 있어 파일이 제외되지는 않았는지\n"
            "3. GitHub 웹 UI로 파일을 업로드했다면, 폴더째 드래그했을 때 하위 폴더 구조가 "
            "깨지지 않았는지 (data/KBO.dta가 아니라 리포지토리 루트에 KBO.dta로 올라간 경우가 흔합니다)"
        )
        st.stop()

    file_size = os.path.getsize(DATA_PATH)
    with open(DATA_PATH, "rb") as f:
        header_preview = f.read(200)

    try:
        df = pd.read_stata(DATA_PATH)
    except Exception as read_err:
        # 흔한 원인: Git LFS로 추적되는 파일인데 배포 환경이 LFS를 지원하지 않아
        # 실제 데이터 대신 'LFS 포인터'라는 작은 텍스트 파일만 받아온 경우.
        # (Streamlit Community Cloud는 기본적으로 Git LFS를 지원하지 않습니다.)
        is_lfs_pointer = header_preview.startswith(b"version https://git-lfs")
        st.error(
            "❌ data/KBO.dta 파일을 찾긴 했지만, Stata 파일로 읽는 데 실패했습니다.\n\n"
            f"파일 크기: {file_size:,} bytes (정상 파일은 약 5,656,011 bytes)\n"
            f"파일 앞부분 미리보기: `{header_preview[:120]!r}`\n\n"
            + (
                "**원인 추정: Git LFS 포인터 파일입니다.** "
                "이 파일이 실제 데이터가 아니라 Git LFS 포인터(안내용 텍스트)로 저장되어 있습니다. "
                "Streamlit Community Cloud는 Git LFS를 지원하지 않아 포인터 파일만 받아오면 이런 에러가 납니다.\n"
                "해결: 리포지토리에서 `.gitattributes`에 `*.dta filter=lfs ...` 같은 줄이 있다면 삭제하고, "
                "`git lfs untrack \"*.dta\"` 후 파일을 일반 파일로 다시 커밋해주세요."
                if is_lfs_pointer else
                "**원인 추정: 파일이 손상되었거나 올바른 .dta 파일이 아닙니다.** "
                "업로드 과정에서 파일이 손상되었을 수 있습니다 (예: 텍스트 모드로 변환되어 저장, 잘못된 파일을 같은 이름으로 업로드 등). "
                "로컬에서 파일을 다시 다운로드해 `data/KBO.dta` 자리에 원본 그대로 다시 올려주세요."
            )
            + f"\n\n(원본 에러: {read_err})"
        )
        st.stop()

    for col in SIMPLE_NUMERIC_STRING_COLS:
        if col in df.columns:
            df[col] = df[col].apply(_clean_numeric_string)
    for col in FRACTION_STRING_COLS:
        if col in df.columns:
            df[col] = df[col].apply(_innings_to_float)
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
