from __future__ import annotations

import pandas as pd

from src.scoring import normalize_region, split_keywords


def build_reason(row: pd.Series, user_profile: dict) -> str:
    reasons: list[str] = []
    preferred_provinces = {normalize_region(item) for item in split_keywords(user_profile.get("preferred_provinces"))}
    preferred_cities = set(split_keywords(user_profile.get("preferred_cities")))
    preferred_levels = split_keywords(user_profile.get("preferred_university_levels"))
    preferred_keywords = split_keywords(user_profile.get("preferred_major_keywords"))

    if row.get("tier"):
        reasons.append(f"位次匹配属于{row['tier']}档")
    if preferred_provinces and normalize_region(row.get("school_province")) in preferred_provinces:
        reasons.append("符合意向省份")
    if preferred_cities and str(row.get("city") or "") in preferred_cities:
        reasons.append("符合意向城市")
    if preferred_levels and any(level in str(row.get("university_level") or "") for level in preferred_levels):
        reasons.append("符合意向院校层次")
    if preferred_keywords:
        major_text = str(row.get("major_name") or "")
        matched_keywords = [keyword for keyword in preferred_keywords if keyword in major_text]
        if matched_keywords:
            reasons.append("专业关键词匹配：" + "、".join(matched_keywords))
    if float(row.get("employment_rate") or 0) > 0:
        reasons.append(f"就业率参考值 {float(row['employment_rate']):.0%}")
    if float(row.get("public_exam_fit_score") or 0) >= 0.75:
        reasons.append("考公适配度较高")

    return "；".join(reasons) if reasons else "基于位次、地区、院校和专业偏好生成的数据库内推荐。"


def build_risk_warning(row: pd.Series, current_rank: int) -> str:
    tier = str(row.get("tier") or "")
    rank_diff = float(row.get("rank_diff") or 0)
    if tier == "冲":
        return "往年最低位次优于当前位次，存在一定冲刺风险。"
    if tier == "稳":
        return "往年最低位次与当前位次接近，仍需结合当年招生计划变化判断。"
    if tier == "保":
        return "往年最低位次低于当前位次，风险相对较低，但不代表一定录取。"
    if current_rank and abs(rank_diff) > current_rank * 0.3:
        return "位次差距较大，请谨慎参考。"
    return "暂无明确风险提示。"
