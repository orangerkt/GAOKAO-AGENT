from __future__ import annotations

import math
from typing import Iterable

import pandas as pd


PROVINCE_SUFFIXES = ("自治区", "特别行政区", "省", "市")


def normalize_region(value: object) -> str:
    text = str(value or "").strip()
    for suffix in PROVINCE_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text


def split_keywords(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        raw_values = values.replace("，", ",").replace("；", ",").replace(";", ",").split(",")
    else:
        raw_values = values
    return [str(value).strip() for value in raw_values if str(value).strip()]


def classify_tier(min_rank: float | int | None, current_rank: int) -> str:
    if not min_rank or not current_rank:
        return "未知"

    rank_diff = float(min_rank) - float(current_rank)
    if abs(rank_diff) / float(current_rank) <= 0.10:
        return "稳"
    if rank_diff < 0:
        return "冲"
    return "保"


def get_university_level(row: pd.Series) -> str:
    levels: list[str] = []
    if int(row.get("is_985") or 0) == 1:
        levels.append("985")
    if int(row.get("is_211") or 0) == 1:
        levels.append("211")
    if int(row.get("is_double_first_class") or 0) == 1:
        levels.append("双一流")
    return " / ".join(levels) if levels else "普通本科"


def _rank_score(rank_diff: float, current_rank: int) -> float:
    if current_rank <= 0 or math.isnan(rank_diff):
        return 0.0
    return max(0.0, 1.0 - min(abs(rank_diff) / current_rank, 1.0))


def _location_score(row: pd.Series, preferred_provinces: list[str], preferred_cities: list[str]) -> float:
    school_province = normalize_region(row.get("school_province"))
    city = str(row.get("city") or "").strip()
    province_matches = {normalize_region(province) for province in preferred_provinces}
    city_matches = {str(item).strip() for item in preferred_cities}

    if not province_matches and not city_matches:
        return 0.5

    score = 0.0
    if province_matches and school_province in province_matches:
        score += 0.45
    if city_matches and city in city_matches:
        score += 0.55
    return min(score, 1.0)


def _university_level_score(university_level: str, preferred_levels: list[str]) -> float:
    if not preferred_levels:
        return 0.5
    return 1.0 if any(level in university_level for level in preferred_levels) else 0.0


def _major_keyword_score(row: pd.Series, keywords: list[str]) -> float:
    if not keywords:
        return 0.5
    text = f"{row.get('major_name') or ''} {row.get('major_category') or ''}"
    return 1.0 if any(keyword in text for keyword in keywords) else 0.0


def _risk_score(tier: str, risk_preference: str) -> float:
    if risk_preference == "冲刺":
        return {"冲": 1.0, "稳": 0.7, "保": 0.4}.get(tier, 0.3)
    if risk_preference == "稳妥":
        return {"保": 1.0, "稳": 0.75, "冲": 0.25}.get(tier, 0.3)
    return {"稳": 1.0, "保": 0.75, "冲": 0.55}.get(tier, 0.3)


def calculate_total_score(row: pd.Series, user_profile: dict) -> float:
    current_rank = int(user_profile.get("current_rank") or 0)
    preferred_provinces = split_keywords(user_profile.get("preferred_provinces"))
    preferred_cities = split_keywords(user_profile.get("preferred_cities"))
    preferred_levels = split_keywords(user_profile.get("preferred_university_levels"))
    preferred_keywords = split_keywords(user_profile.get("preferred_major_keywords"))
    risk_preference = str(user_profile.get("risk_preference") or "均衡")

    rank_score = _rank_score(float(row.get("rank_diff") or 0), current_rank)
    location_score = _location_score(row, preferred_provinces, preferred_cities)
    level_score = _university_level_score(str(row.get("university_level") or ""), preferred_levels)
    major_score = _major_keyword_score(row, preferred_keywords)
    employment_score = float(row.get("employment_rate") or 0)
    postgraduate_score = max(
        float(row.get("postgraduate_rate") or 0),
        float(row.get("recommended_graduate_rate") or 0),
    )
    public_exam_score = float(row.get("public_exam_fit_score") or 0)
    risk_score = _risk_score(str(row.get("tier") or ""), risk_preference)

    total = (
        rank_score * 0.30
        + location_score * 0.12
        + level_score * 0.14
        + major_score * 0.16
        + employment_score * 0.10
        + postgraduate_score * 0.08
        + public_exam_score * 0.05
        + risk_score * 0.05
    )
    return round(total * 100, 2)
