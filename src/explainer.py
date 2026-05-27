from __future__ import annotations

import pandas as pd

from src.scoring import normalize_region, split_keywords


def _has_value(row: pd.Series, column: str) -> bool:
    value = row.get(column)
    if pd.isna(value):
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _format_percent(row: pd.Series, column: str) -> str | None:
    if not _has_value(row, column):
        return None
    value = float(row.get(column) or 0)
    if value <= 0:
        return None
    return f"{value:.0%}"


def generate_reason(row: pd.Series, user_profile: dict) -> str:
    reasons: list[str] = []
    current_rank = int(user_profile.get("current_rank") or 0)
    rank_diff = float(row.get("rank_diff") or 0)
    tier = str(row.get("tier") or "")

    preferred_provinces = {normalize_region(item) for item in split_keywords(user_profile.get("preferred_provinces"))}
    preferred_cities = set(split_keywords(user_profile.get("preferred_cities")))
    preferred_levels = split_keywords(user_profile.get("preferred_university_levels"))
    preferred_keywords = split_keywords(user_profile.get("preferred_major_keywords"))

    if tier and current_rank:
        if tier == "冲":
            reasons.append(f"往年最低位次比当前位次靠前 {abs(int(rank_diff))} 名，归为冲刺参考")
        elif tier == "稳":
            reasons.append(f"往年最低位次与当前位次差距 {abs(int(rank_diff))} 名，归为稳妥参考")
        elif tier == "保":
            reasons.append(f"往年最低位次比当前位次靠后 {abs(int(rank_diff))} 名，归为保底参考")
        else:
            reasons.append("位次信息可用于排序参考")

    school_province = normalize_region(row.get("school_province"))
    city = str(row.get("city") or "").strip()
    if preferred_provinces:
        if school_province in preferred_provinces:
            reasons.append(f"院校省份 {row.get('school_province')} 符合意向地区")
        else:
            reasons.append(f"院校省份为 {row.get('school_province')}，不在当前意向地区内")
    if preferred_cities:
        if city in preferred_cities:
            reasons.append(f"城市 {city} 符合偏好")
        else:
            reasons.append(f"城市为 {city}，不在当前意向城市内")

    university_level = str(row.get("university_level") or "")
    if preferred_levels:
        matched_levels = [level for level in preferred_levels if level in university_level]
        if matched_levels:
            reasons.append("院校层次匹配：" + "、".join(matched_levels))
        else:
            reasons.append(f"院校层次为 {university_level}，未匹配当前层次偏好")

    major_name = str(row.get("major_name") or "")
    if preferred_keywords:
        matched_keywords = [keyword for keyword in preferred_keywords if keyword in major_name]
        if matched_keywords:
            reasons.append("专业关键词匹配：" + "、".join(matched_keywords))
        else:
            reasons.append(f"专业为 {major_name}，未命中当前专业关键词")

    employment_rate = _format_percent(row, "employment_rate")
    if employment_rate:
        reasons.append(f"就业率字段有数据：{employment_rate}")
    else:
        reasons.append("就业率字段暂无可用数据")

    postgraduate_rate = _format_percent(row, "postgraduate_rate")
    recommended_graduate_rate = _format_percent(row, "recommended_graduate_rate")
    if postgraduate_rate:
        reasons.append(f"升学率字段有数据：{postgraduate_rate}")
    if recommended_graduate_rate:
        reasons.append(f"保研/推免参考字段有数据：{recommended_graduate_rate}")
    if not postgraduate_rate and not recommended_graduate_rate:
        reasons.append("升学率和保研/推免参考字段暂无可用数据")

    public_exam_fit_score = float(row.get("public_exam_fit_score") or 0)
    if public_exam_fit_score >= 0.75:
        reasons.append(f"考公适配度较高：{public_exam_fit_score:.2f}")
    elif public_exam_fit_score > 0:
        reasons.append(f"考公适配度参考值：{public_exam_fit_score:.2f}")
    else:
        reasons.append("考公适配度暂无可用数据")

    return "；".join(reasons)


def generate_risk_warning(row: pd.Series, current_rank: int) -> str:
    warnings: list[str] = []
    tier = str(row.get("tier") or "")
    rank_diff = float(row.get("rank_diff") or 0)
    plan_count = float(row.get("plan_count") or 0)

    if tier == "冲":
        warnings.append("该项属于冲刺档，录取不确定性相对较高")
    if plan_count > 0 and plan_count <= 3:
        warnings.append("招生计划数较少，录取位次波动风险可能较大")
    if bool(row.get("employment_rate_missing")):
        warnings.append("就业率暂无可靠数据")
    if bool(row.get("recommended_graduate_rate_missing")):
        warnings.append("保研/推免参考数据暂无可靠数据")
    if current_rank and abs(rank_diff) / current_rank >= 0.30:
        warnings.append("位次差距明显，请结合近年波动进一步判断")

    if warnings:
        return "；".join(warnings) + "。"
    return "未发现明显单项风险，但仍需结合当年招生计划、考生位次分布和院校专业热度变化判断。"


build_reason = generate_reason
build_risk_warning = generate_risk_warning
