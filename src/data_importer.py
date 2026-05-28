from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from src.database import get_connection, init_db
from src.utils import get_data_dir


PDF_SAVED_ONLY_MESSAGE = (
    "PDF 文件已保存并登记，当前版本暂不执行复杂表格解析。"
    "后续可接入 pdfplumber/camelot。"
)

DATA_TYPE_TO_TABLE = {
    "一分一段表": "score_rank",
    "批次线": "control_lines",
    "招生计划": "admission_plans",
    "投档线": "admission_results",
    "录取结果": "admission_results",
    "选科要求": "subject_requirements",
    "招生章程": "charter_constraints",
    "公务员岗位表": "civil_service_positions",
}
SAVE_ONLY_DATA_TYPES = {"就业质量报告", "保研/推免数据"}

TABLE_COLUMNS = {
    "score_rank": [
        "year",
        "province",
        "category",
        "score",
        "cumulative_count",
        "source_file",
        "source_url",
    ],
    "control_lines": [
        "year",
        "province",
        "category",
        "batch",
        "control_score",
        "source_file",
        "source_url",
    ],
    "admission_plans": [
        "year",
        "province",
        "category",
        "batch",
        "university_code",
        "university_name",
        "major_group_code",
        "major_code",
        "major_name",
        "plan_count",
        "tuition",
        "duration",
        "subject_requirement",
        "remarks",
        "source_file",
        "source_url",
    ],
    "admission_results": [
        "year",
        "province",
        "category",
        "batch",
        "university_code",
        "university_name",
        "major_group_code",
        "major_name",
        "min_score",
        "min_rank",
        "max_score",
        "max_rank",
        "admitted_count",
        "source_file",
        "source_url",
    ],
    "subject_requirements": [
        "year",
        "university_code",
        "university_name",
        "major_code",
        "major_name",
        "subject_requirement",
        "source_file",
        "source_url",
    ],
    "charter_constraints": [
        "year",
        "university_name",
        "major_name",
        "constraint_type",
        "constraint_value",
        "source_file",
        "source_url",
    ],
    "civil_service_positions": [
        "year",
        "exam_type",
        "department",
        "position_name",
        "region",
        "education_requirement",
        "degree_requirement",
        "major_requirement",
        "political_requirement",
        "work_experience_requirement",
        "recruit_count",
        "source_file",
        "source_url",
    ],
}

FIELD_ALIASES = {
    "score_rank": {
        "score": ["分数", "成绩", "总分", "score"],
        "cumulative_count": ["累计人数", "累计", "位次", "累计位次", "排名", "rank", "cumulative_count"],
        "category": ["科类", "类别", "首选科目", "category"],
    },
    "control_lines": {
        "batch": ["批次", "录取批次", "batch"],
        "control_score": ["控制线", "分数线", "最低控制分数线", "control_score"],
        "category": ["科类", "类别", "首选科目", "category"],
    },
    "admission_plans": {
        "university_code": ["院校代码", "学校代码", "院校代号"],
        "university_name": ["院校名称", "学校名称", "招生院校"],
        "major_group_code": ["专业组代码", "院校专业组", "专业组"],
        "major_code": ["专业代码", "专业代号"],
        "major_name": ["专业名称", "招生专业"],
        "category": ["科类", "类别", "首选科目"],
        "batch": ["批次", "录取批次"],
        "plan_count": ["计划数", "招生计划", "招生人数", "计划人数"],
        "tuition": ["学费", "收费标准"],
        "duration": ["学制", "修业年限"],
        "subject_requirement": ["选科要求", "科目要求", "再选科目要求"],
        "remarks": ["备注", "说明"],
    },
    "admission_results": {
        "university_code": ["院校代码", "学校代码", "院校代号"],
        "university_name": ["院校名称", "学校名称", "招生院校"],
        "major_group_code": ["专业组代码", "院校专业组", "专业组"],
        "major_name": ["专业名称", "招生专业"],
        "category": ["科类", "类别", "首选科目"],
        "batch": ["批次", "录取批次"],
        "min_score": ["最低分", "投档最低分", "录取最低分"],
        "min_rank": ["最低位次", "投档最低位次", "录取最低位次", "位次"],
        "max_score": ["最高分", "录取最高分", "投档最高分"],
        "max_rank": ["最高位次"],
        "admitted_count": ["录取人数", "投档人数", "计划数"],
    },
    "subject_requirements": {
        "university_code": ["院校代码", "学校代码"],
        "university_name": ["院校名称", "学校名称"],
        "major_code": ["专业代码", "专业代号"],
        "major_name": ["专业名称", "招生专业"],
        "subject_requirement": ["选科要求", "科目要求", "再选科目要求"],
    },
    "charter_constraints": {
        "university_name": ["院校名称", "学校名称", "招生院校"],
        "major_name": ["专业名称", "招生专业"],
        "constraint_type": ["限制类型", "约束类型", "规则类型", "constraint_type"],
        "constraint_value": ["限制内容", "约束内容", "规则内容", "constraint_value"],
    },
    "civil_service_positions": {
        "exam_type": ["考试类型", "招考类型"],
        "department": ["部门", "招录机关", "单位名称"],
        "position_name": ["职位名称", "岗位名称"],
        "region": ["地区", "工作地点", "工作地区"],
        "education_requirement": ["学历要求", "学历"],
        "degree_requirement": ["学位要求", "学位"],
        "major_requirement": ["专业要求", "专业"],
        "political_requirement": ["政治面貌", "政治面貌要求"],
        "work_experience_requirement": ["基层工作经历", "工作经历要求"],
        "recruit_count": ["招录人数", "招聘人数", "计划人数"],
    },
}

NUMERIC_COLUMNS = {
    "score_rank": ["year", "score", "cumulative_count"],
    "control_lines": ["year", "control_score"],
    "admission_plans": ["year", "plan_count", "tuition"],
    "admission_results": ["year", "min_score", "min_rank", "max_score", "max_rank", "admitted_count"],
    "subject_requirements": ["year"],
    "charter_constraints": ["year"],
    "civil_service_positions": ["year", "recruit_count"],
}

REQUIRED_FIELDS = {
    "score_rank": ["year", "province", "category", "score", "cumulative_count"],
    "control_lines": ["year", "province", "category", "batch", "control_score"],
    "admission_plans": ["year", "province", "university_name", "major_name", "plan_count"],
    "admission_results": ["year", "province", "university_name"],
    "subject_requirements": ["year", "university_name", "major_name", "subject_requirement"],
    "charter_constraints": ["year", "university_name", "constraint_type", "constraint_value"],
    "civil_service_positions": ["year", "exam_type", "department", "position_name", "major_requirement"],
}

NULL_TOKENS = {"", "-", "—", "无", "暂无", "nan", "none"}
SOURCE_COLUMNS = {"source_file", "source_url"}


@dataclass(frozen=True)
class RawFileRecord:
    id: int
    saved_path: Path
    parse_status: str | None
    parse_message: str | None


def get_target_table(data_type: str) -> str | None:
    return DATA_TYPE_TO_TABLE.get(str(data_type or "").strip())


def is_save_only_data_type(data_type: str) -> bool:
    return str(data_type or "").strip() in SAVE_ONLY_DATA_TYPES


def normalize_empty_value(value: object) -> object | None:
    if value is None:
        return None
    if pd.isna(value):
        return None
    if isinstance(value, str):
        text = value.strip()
        if text.lower() in NULL_TOKENS:
            return None
        return text
    return value


def normalize_empty_values(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.astype("object").where(pd.notna(df), None)
    for column in normalized.columns:
        normalized[column] = normalized[column].map(normalize_empty_value)
    return normalized


def _normalize_column_name(column: object) -> str:
    return re.sub(r"\s+", "", str(column or "").strip()).lower()


def _safe_path_part(value: object) -> str:
    text = str(value or "unknown").strip() or "unknown"
    return re.sub(r'[\\/:*?"<>|]+', "_", text)


def _uploaded_file_bytes(uploaded_file: BinaryIO | bytes) -> bytes:
    if isinstance(uploaded_file, bytes):
        return uploaded_file
    if hasattr(uploaded_file, "getbuffer"):
        return bytes(uploaded_file.getbuffer())
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    data = uploaded_file.read()
    return data if isinstance(data, bytes) else bytes(data)


def save_uploaded_file(uploaded_file: BinaryIO | bytes, year: int, data_type: str) -> Path:
    original_name = getattr(uploaded_file, "name", "uploaded_file")
    original_path = Path(str(original_name))
    suffix = original_path.suffix.lower()
    stem = _safe_path_part(original_path.stem or "uploaded_file")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_name = f"{stem}_{timestamp}_{uuid.uuid4().hex[:8]}{suffix}"

    target_dir = get_data_dir() / "uploads" / "raw" / str(year) / _safe_path_part(data_type)
    target_dir.mkdir(parents=True, exist_ok=True)
    saved_path = target_dir / unique_name
    saved_path.write_bytes(_uploaded_file_bytes(uploaded_file))
    return saved_path


def create_raw_file_record(
    *,
    file_name: str,
    file_type: str,
    data_type: str,
    year: int,
    source_name: str | None,
    source_url: str | None,
    saved_path: Path,
    parse_status: str,
    parse_message: str | None = None,
) -> int:
    init_db()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO raw_files (
                file_name,
                file_type,
                data_type,
                year,
                source_name,
                source_url,
                saved_path,
                parse_status,
                parse_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_name,
                file_type,
                data_type,
                year,
                source_name,
                source_url,
                str(saved_path),
                parse_status,
                parse_message,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def update_raw_file_status(raw_file_id: int, parse_status: str, parse_message: str | None) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE raw_files
            SET parse_status = ?, parse_message = ?
            WHERE id = ?
            """,
            (parse_status, parse_message, raw_file_id),
        )
        connection.commit()


def save_and_register_upload(
    uploaded_file: BinaryIO | bytes,
    *,
    year: int,
    data_type: str,
    source_name: str | None,
    source_url: str | None,
) -> RawFileRecord:
    saved_path = save_uploaded_file(uploaded_file, year, data_type)
    file_type = saved_path.suffix.lower().lstrip(".")
    is_pdf = file_type == "pdf"
    parse_status = "saved_only" if is_pdf else "uploaded"
    parse_message = PDF_SAVED_ONLY_MESSAGE if is_pdf else None
    raw_file_id = create_raw_file_record(
        file_name=Path(str(getattr(uploaded_file, "name", saved_path.name))).name,
        file_type=file_type,
        data_type=data_type,
        year=year,
        source_name=source_name,
        source_url=source_url,
        saved_path=saved_path,
        parse_status=parse_status,
        parse_message=parse_message,
    )
    return RawFileRecord(raw_file_id, saved_path, parse_status, parse_message)


def read_tabular_file(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
    if suffix == ".xlsx":
        return pd.read_excel(file_path, engine="openpyxl")
    if suffix == ".xls":
        return pd.read_excel(file_path, engine="xlrd")
    raise ValueError(f"暂不支持读取该文件类型：{suffix}")


def guess_field_mapping(table_name: str, columns: list[object]) -> dict[str, str | None]:
    aliases = FIELD_ALIASES.get(table_name, {})
    normalized_columns = {_normalize_column_name(column): str(column) for column in columns}
    mapping: dict[str, str | None] = {}

    for target_column in TABLE_COLUMNS.get(table_name, []):
        if target_column in SOURCE_COLUMNS or target_column in {"year", "province"}:
            continue

        candidates = [target_column, *aliases.get(target_column, [])]
        matched_column = None
        for candidate in candidates:
            matched_column = normalized_columns.get(_normalize_column_name(candidate))
            if matched_column:
                break
        mapping[target_column] = matched_column

    return mapping


def get_mappable_columns(table_name: str) -> list[str]:
    return [
        column
        for column in TABLE_COLUMNS.get(table_name, [])
        if column not in SOURCE_COLUMNS and column not in {"year", "province"}
    ]


def build_standard_dataframe(
    raw_df: pd.DataFrame,
    *,
    table_name: str,
    field_mapping: dict[str, str | None],
    year: int | None,
    province: str | None,
    category: str | None,
    source_file: str,
    source_url: str | None,
) -> pd.DataFrame:
    raw_df = normalize_empty_values(raw_df)
    standard = pd.DataFrame(index=raw_df.index)

    metadata = {
        "year": year,
        "province": normalize_empty_value(province),
        "category": normalize_empty_value(category),
        "source_file": source_file,
        "source_url": normalize_empty_value(source_url),
    }

    for column in TABLE_COLUMNS[table_name]:
        metadata_value = metadata.get(column)
        mapped_column = field_mapping.get(column)

        if metadata_value is not None:
            standard[column] = metadata_value
        elif mapped_column and mapped_column in raw_df.columns:
            standard[column] = raw_df[mapped_column]
        else:
            standard[column] = None

    standard = normalize_empty_values(standard)
    for column in NUMERIC_COLUMNS.get(table_name, []):
        if column not in standard.columns:
            continue
        numeric = pd.to_numeric(standard[column], errors="coerce")
        standard[column] = numeric.astype("object").where(pd.notna(numeric), None)

    return standard


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if pd.isna(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _valid_required_mask(df: pd.DataFrame, table_name: str) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool)

    mask = pd.Series(True, index=df.index)
    for field in REQUIRED_FIELDS.get(table_name, []):
        if field not in df.columns:
            mask &= False
        else:
            mask &= ~df[field].map(_is_missing)

    if table_name == "admission_results":
        score_rank_available = (~df["min_score"].map(_is_missing)) | (~df["min_rank"].map(_is_missing))
        mask &= score_rank_available

    return mask


def _build_quality_report(
    *,
    table_name: str,
    raw_df: pd.DataFrame,
    standard_df: pd.DataFrame,
    field_mapping: dict[str, str | None],
    valid_mask: pd.Series,
    duplicate_count: int,
    imported_count: int,
) -> dict:
    total_rows = int(len(raw_df))
    missing_key_rows = int(total_rows - valid_mask.sum())
    recognized_columns = {column for column in field_mapping.values() if column}
    unrecognized_columns = [str(column) for column in raw_df.columns if str(column) not in recognized_columns]

    suggestions = []
    if missing_key_rows:
        suggestions.append("存在关键字段缺失行，请检查字段映射或原始数据。")
    if duplicate_count:
        suggestions.append("存在重复行，当前导入时已按标准字段去重。")
    if unrecognized_columns:
        suggestions.append("存在未映射字段，请确认是否需要补充到标准字段。")
    if imported_count == 0 and total_rows:
        suggestions.append("没有可导入数据，请优先检查关键字段。")

    return {
        "target_table": table_name,
        "total_rows": total_rows,
        "imported_rows": int(imported_count),
        "missing_key_rows": missing_key_rows,
        "duplicate_rows": int(duplicate_count),
        "unrecognized_columns": unrecognized_columns,
        "suggestions": suggestions,
        "standard_columns": list(standard_df.columns),
    }


def _status_from_report(report: dict) -> str:
    total_rows = int(report.get("total_rows") or 0)
    imported_rows = int(report.get("imported_rows") or 0)
    duplicate_rows = int(report.get("duplicate_rows") or 0)
    missing_key_rows = int(report.get("missing_key_rows") or 0)

    if imported_rows <= 0:
        return "failed"
    if imported_rows == total_rows and duplicate_rows == 0 and missing_key_rows == 0:
        return "imported"
    return "partial"


def _message_from_report(report: dict) -> str:
    return (
        f"总行数 {report['total_rows']}，成功导入 {report['imported_rows']}，"
        f"缺失关键字段 {report['missing_key_rows']}，重复行 {report['duplicate_rows']}。"
    )


def import_dataframe_to_standard_table(
    *,
    raw_file_id: int,
    raw_df: pd.DataFrame,
    data_type: str,
    field_mapping: dict[str, str | None],
    year: int | None,
    province: str | None,
    category: str | None,
    source_file: str,
    source_url: str | None,
) -> dict:
    table_name = get_target_table(data_type)
    if table_name is None:
        message = "该数据类型当前版本仅保存原始文件，不执行结构化入库。"
        update_raw_file_status(raw_file_id, "saved_only", message)
        return {
            "target_table": None,
            "total_rows": int(len(raw_df)),
            "imported_rows": 0,
            "missing_key_rows": 0,
            "duplicate_rows": 0,
            "unrecognized_columns": [str(column) for column in raw_df.columns],
            "suggestions": [message],
            "standard_columns": [],
        }

    standard_df = build_standard_dataframe(
        raw_df,
        table_name=table_name,
        field_mapping=field_mapping,
        year=year,
        province=province,
        category=category,
        source_file=source_file,
        source_url=source_url,
    )
    valid_mask = _valid_required_mask(standard_df, table_name)
    valid_df = standard_df[valid_mask].copy()
    duplicate_count = int(valid_df.duplicated().sum())
    valid_df = valid_df.drop_duplicates()
    imported_count = int(len(valid_df))

    if imported_count:
        with get_connection() as connection:
            valid_df.to_sql(table_name, connection, if_exists="append", index=False)
            connection.commit()

    report = _build_quality_report(
        table_name=table_name,
        raw_df=raw_df,
        standard_df=standard_df,
        field_mapping=field_mapping,
        valid_mask=valid_mask,
        duplicate_count=duplicate_count,
        imported_count=imported_count,
    )
    status = _status_from_report(report)
    update_raw_file_status(raw_file_id, status, _message_from_report(report))
    return report
