from __future__ import annotations

import sqlite3

import pandas as pd

from src.database import get_connection
from src.explainer import generate_reason, generate_risk_warning
from src.scoring import calculate_total_score, classify_tier, get_university_level


RECOMMENDATION_COLUMNS = [
    "tier",
    "university_name",
    "major_name",
    "school_province",
    "city",
    "university_level",
    "min_score",
    "min_rank",
    "plan_count",
    "rank_diff",
    "employment_rate",
    "postgraduate_rate",
    "recommended_graduate_rate",
    "public_exam_fit_score",
    "total_score",
    "reason",
    "risk_warning",
]


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)


def _read_table(connection: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(f"SELECT * FROM {table_name}", connection)
    except (sqlite3.Error, pd.errors.DatabaseError):
        return pd.DataFrame()


def _merge_profiles(
    admissions: pd.DataFrame,
    universities: pd.DataFrame,
    majors: pd.DataFrame,
    employment: pd.DataFrame,
) -> pd.DataFrame:
    result = admissions.copy()

    if not universities.empty:
        university_columns = [column for column in universities.columns if column != "id"]
        result = result.merge(
            universities[university_columns],
            on=["university_name", "school_province", "city"],
            how="left",
        )

    if not majors.empty:
        major_columns = [column for column in majors.columns if column != "id"]
        result = result.merge(majors[major_columns], on="major_name", how="left")

    if not employment.empty:
        employment_columns = [column for column in employment.columns if column != "id"]
        result = result.merge(
            employment[employment_columns],
            on=["university_name", "major_name"],
            how="left",
        )

    return result


def recommend_programs(user_profile: dict) -> pd.DataFrame:
    current_rank = int(user_profile.get("current_rank") or 0)
    category = str(user_profile.get("category") or "").strip()
    top_k = int(user_profile.get("top_k") or 30)

    if current_rank <= 0 or not category:
        return _empty_result()

    with get_connection() as connection:
        admissions = _read_table(connection, "admission_records")
        universities = _read_table(connection, "university_profiles")
        majors = _read_table(connection, "major_profiles")
        employment = _read_table(connection, "employment_profiles")

    if admissions.empty or "category" not in admissions.columns:
        return _empty_result()

    admissions = admissions[admissions["category"].astype(str).str.strip() == category].copy()
    if admissions.empty:
        return _empty_result()

    result = _merge_profiles(admissions, universities, majors, employment)
    numeric_columns = [
        "min_score",
        "min_rank",
        "plan_count",
        "employment_rate",
        "postgraduate_rate",
        "recommended_graduate_rate",
        "public_exam_fit_score",
        "is_985",
        "is_211",
        "is_double_first_class",
    ]
    for column in numeric_columns:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")

    for column in ["employment_rate", "postgraduate_rate", "recommended_graduate_rate"]:
        missing_column = f"{column}_missing"
        if column in result.columns:
            result[missing_column] = result[column].isna()
        else:
            result[missing_column] = True

    for column in [
        "employment_rate",
        "postgraduate_rate",
        "recommended_graduate_rate",
        "public_exam_fit_score",
        "is_985",
        "is_211",
        "is_double_first_class",
    ]:
        if column not in result.columns:
            result[column] = 0
        result[column] = result[column].fillna(0)

    result = result.dropna(subset=["min_rank"]).copy()
    if result.empty:
        return _empty_result()

    result["rank_diff"] = result["min_rank"] - current_rank
    result["tier"] = result["min_rank"].apply(lambda min_rank: classify_tier(min_rank, current_rank))
    result["university_level"] = result.apply(get_university_level, axis=1)
    result["total_score"] = result.apply(lambda row: calculate_total_score(row, user_profile), axis=1)
    result["reason"] = result.apply(lambda row: generate_reason(row, user_profile), axis=1)
    result["risk_warning"] = result.apply(lambda row: generate_risk_warning(row, current_rank), axis=1)

    result = result.sort_values(
        by=["total_score", "tier", "min_rank"],
        ascending=[False, True, True],
    )

    return result[RECOMMENDATION_COLUMNS].head(top_k).reset_index(drop=True)
