from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "KBO.dta"


def _to_numeric(series: pd.Series) -> pd.Series:
    """Convert KBO text-formatted numeric columns, treating '-' and blanks as missing."""
    return pd.to_numeric(
        series.astype("string").str.strip().replace({"": pd.NA, "-": pd.NA}),
        errors="coerce",
    )


def innings_to_float(value: object) -> float:
    """Convert baseball innings such as '159 2/3' to 159.6667."""
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if not text or text == "-":
        return np.nan
    try:
        if " " not in text:
            return float(text)
        whole, fraction = text.split(maxsplit=1)
        numerator, denominator = fraction.split("/")
        return float(whole) + float(numerator) / float(denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return np.nan


@st.cache_data(show_spinner=False)
def load_data(path: str | Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Read and standardize the Stata dataset."""
    data_path = Path(path)
    if not data_path.exists():
        raise FileNotFoundError(
            f"데이터 파일을 찾을 수 없습니다: {data_path}. "
            "KBO.dta를 프로젝트의 data/ 폴더에 넣어 주십시오."
        )

    df = pd.read_stata(data_path)
    df.columns = [str(col).strip() for col in df.columns]

    text_columns = ["player_name", "team", "def_POS"]
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # Inning columns use baseball fractions (1/3, 2/3), so preserve semantics.
    for col in ["def_IP", "pit_IP"]:
        if col in df.columns:
            df[f"{col}_num"] = df[col].map(innings_to_float)

    id_columns = {"player_name", "player_id", "year", "team", "def_POS", "def_IP", "pit_IP"}
    for col in df.columns:
        if col not in id_columns and df[col].dtype == "object":
            converted = _to_numeric(df[col])
            # Convert when at least one valid number exists or the original column is all blank/'-'.
            if converted.notna().any() or df[col].astype("string").str.strip().isin(["", "-"]).all():
                df[col] = converted

    # Derived batting measures used in several pages.
    if {"hit_H", "hit_2B", "hit_3B", "hit_HR"}.issubset(df.columns):
        df["hit_1B"] = (
            df["hit_H"].fillna(0)
            - df["hit_2B"].fillna(0)
            - df["hit_3B"].fillna(0)
            - df["hit_HR"].fillna(0)
        ).clip(lower=0)

    if {"hit_TB", "hit_BB", "hit_HBP", "hit_AB", "hit_SF"}.issubset(df.columns):
        denominator = (
            df["hit_AB"].fillna(0)
            + df["hit_BB"].fillna(0)
            + df["hit_HBP"].fillna(0)
            + df["hit_SF"].fillna(0)
        )
        df["hit_wOBA_simple"] = np.where(
            denominator > 0,
            (
                0.69 * df["hit_BB"].fillna(0)
                + 0.72 * df["hit_HBP"].fillna(0)
                + 0.89 * df["hit_1B"].fillna(0)
                + 1.27 * df["hit_2B"].fillna(0)
                + 1.62 * df["hit_3B"].fillna(0)
                + 2.10 * df["hit_HR"].fillna(0)
            )
            / denominator,
            np.nan,
        )

    return df


def filter_data(
    df: pd.DataFrame,
    years: tuple[int, int] | None = None,
    teams: Iterable[str] | None = None,
) -> pd.DataFrame:
    result = df.copy()
    if years is not None:
        result = result[result["year"].between(years[0], years[1])]
    if teams:
        result = result[result["team"].isin(list(teams))]
    return result


def batting_data(df: pd.DataFrame, min_pa: int = 1) -> pd.DataFrame:
    return df[df["hit_PA"].fillna(0) >= min_pa].copy()


def pitching_data(df: pd.DataFrame, min_ip: float = 0.1) -> pd.DataFrame:
    ip_col = "pit_IP_num"
    return df[df[ip_col].fillna(0) >= min_ip].copy()


def format_number(value: float | int | None, digits: int = 0) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.{digits}f}"
