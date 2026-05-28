import sqlite3
from pathlib import Path
from typing import BinaryIO, Union

import pandas as pd

from src.utils import get_data_dir, get_db_path


TABLE_SCHEMAS = {
    "admission_records": {
        "columns": [
            "year",
            "province",
            "category",
            "university_name",
            "major_name",
            "major_group",
            "school_province",
            "city",
            "batch",
            "min_score",
            "min_rank",
            "plan_count",
        ],
        "numeric_columns": ["year", "min_score", "min_rank", "plan_count"],
    },
    "university_profiles": {
        "columns": [
            "university_name",
            "school_province",
            "city",
            "is_985",
            "is_211",
            "is_double_first_class",
            "double_first_class_subjects",
            "school_type",
            "public_or_private",
        ],
        "numeric_columns": ["is_985", "is_211", "is_double_first_class"],
    },
    "major_profiles": {
        "columns": [
            "major_name",
            "major_category",
            "public_exam_fit_score",
            "employment_direction",
            "civil_service_notes",
        ],
        "numeric_columns": ["public_exam_fit_score"],
    },
    "employment_profiles": {
        "columns": [
            "university_name",
            "major_name",
            "employment_rate",
            "postgraduate_rate",
            "recommended_graduate_rate",
            "main_employment_regions",
            "main_employment_industries",
        ],
        "numeric_columns": [
            "employment_rate",
            "postgraduate_rate",
            "recommended_graduate_rate",
        ],
    },
}

TABLE_NAMES = tuple(TABLE_SCHEMAS.keys())
TableCount = Union[int, str]
CsvInput = Union[str, Path, BinaryIO]
RecentRawFileRows = list[dict[str, object]] | None


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection using the configured database path."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Create the initial database tables if they do not already exist."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS admission_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER,
                province TEXT,
                category TEXT,
                university_name TEXT,
                major_name TEXT,
                major_group TEXT,
                school_province TEXT,
                city TEXT,
                batch TEXT,
                min_score REAL,
                min_rank INTEGER,
                plan_count INTEGER
            );

            CREATE TABLE IF NOT EXISTS university_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                university_name TEXT,
                school_province TEXT,
                city TEXT,
                is_985 INTEGER,
                is_211 INTEGER,
                is_double_first_class INTEGER,
                double_first_class_subjects TEXT,
                school_type TEXT,
                public_or_private TEXT
            );

            CREATE TABLE IF NOT EXISTS major_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                major_name TEXT,
                major_category TEXT,
                public_exam_fit_score REAL,
                employment_direction TEXT,
                civil_service_notes TEXT
            );

            CREATE TABLE IF NOT EXISTS employment_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                university_name TEXT,
                major_name TEXT,
                employment_rate REAL,
                postgraduate_rate REAL,
                recommended_graduate_rate REAL,
                main_employment_regions TEXT,
                main_employment_industries TEXT
            );

            CREATE TABLE IF NOT EXISTS raw_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_type TEXT,
                data_type TEXT,
                year INTEGER,
                source_name TEXT,
                source_url TEXT,
                saved_path TEXT NOT NULL,
                upload_time TEXT DEFAULT CURRENT_TIMESTAMP,
                parse_status TEXT,
                parse_message TEXT
            );

            CREATE TABLE IF NOT EXISTS score_rank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER,
                province TEXT,
                category TEXT,
                score INTEGER,
                cumulative_count INTEGER,
                source_file TEXT,
                source_url TEXT
            );

            CREATE TABLE IF NOT EXISTS control_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER,
                province TEXT,
                category TEXT,
                batch TEXT,
                control_score INTEGER,
                source_file TEXT,
                source_url TEXT
            );

            CREATE TABLE IF NOT EXISTS admission_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER,
                province TEXT,
                category TEXT,
                batch TEXT,
                university_code TEXT,
                university_name TEXT,
                major_group_code TEXT,
                major_code TEXT,
                major_name TEXT,
                plan_count INTEGER,
                tuition INTEGER,
                duration TEXT,
                subject_requirement TEXT,
                remarks TEXT,
                source_file TEXT,
                source_url TEXT
            );

            CREATE TABLE IF NOT EXISTS admission_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER,
                province TEXT,
                category TEXT,
                batch TEXT,
                university_code TEXT,
                university_name TEXT,
                major_group_code TEXT,
                major_name TEXT,
                min_score INTEGER,
                min_rank INTEGER,
                max_score INTEGER,
                max_rank INTEGER,
                admitted_count INTEGER,
                source_file TEXT,
                source_url TEXT
            );

            CREATE TABLE IF NOT EXISTS subject_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER,
                university_code TEXT,
                university_name TEXT,
                major_code TEXT,
                major_name TEXT,
                subject_requirement TEXT,
                source_file TEXT,
                source_url TEXT
            );

            CREATE TABLE IF NOT EXISTS charter_constraints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER,
                university_name TEXT,
                major_name TEXT,
                constraint_type TEXT,
                constraint_value TEXT,
                source_file TEXT,
                source_url TEXT
            );

            CREATE TABLE IF NOT EXISTS civil_service_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER,
                exam_type TEXT,
                department TEXT,
                position_name TEXT,
                region TEXT,
                education_requirement TEXT,
                degree_requirement TEXT,
                major_requirement TEXT,
                political_requirement TEXT,
                work_experience_requirement TEXT,
                recruit_count INTEGER,
                source_file TEXT,
                source_url TEXT
            );
            """
        )
        connection.commit()


def validate_csv_columns(df: pd.DataFrame, required_columns: list[str]) -> str | None:
    """Check whether a CSV dataframe contains all required columns."""
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        return "CSV 缺少必需字段：" + "、".join(missing_columns)
    return None


def _read_csv(csv_file: CsvInput) -> pd.DataFrame:
    if isinstance(csv_file, (str, Path)):
        csv_path = Path(csv_file)
        if not csv_path.exists():
            raise ValueError(f"CSV 文件不存在：{csv_path}")
        if csv_path.stat().st_size == 0:
            raise ValueError(f"CSV 文件为空：{csv_path}")

    if hasattr(csv_file, "seek"):
        csv_file.seek(0)

    try:
        df = pd.read_csv(csv_file)
    except pd.errors.EmptyDataError as exc:
        raise ValueError("CSV 文件为空，请上传包含表头和数据的文件。") from exc

    if df.empty:
        raise ValueError("CSV 文件没有可导入的数据行。")

    return df


def _convert_numeric_columns(df: pd.DataFrame, numeric_columns: list[str]) -> pd.DataFrame:
    converted = df.copy()
    for column in numeric_columns:
        if column not in converted.columns:
            continue

        original = converted[column]
        numeric = pd.to_numeric(original, errors="coerce")
        invalid_values = original.notna() & original.astype(str).str.strip().ne("") & numeric.isna()
        if invalid_values.any():
            raise ValueError(f"字段 {column} 包含无法转换为数值的值。")
        converted[column] = numeric

    return converted


def import_csv_to_table(csv_file: CsvInput, table_name: str) -> int:
    """Import one CSV file into a known table after validation."""
    if table_name not in TABLE_SCHEMAS:
        raise ValueError(f"不支持的数据表：{table_name}")

    init_db()

    schema = TABLE_SCHEMAS[table_name]
    required_columns = schema["columns"]
    numeric_columns = schema["numeric_columns"]

    df = _read_csv(csv_file)
    error_message = validate_csv_columns(df, required_columns)
    if error_message:
        raise ValueError(error_message)

    df = df[required_columns]
    df = _convert_numeric_columns(df, numeric_columns)

    with get_connection() as connection:
        connection.execute(f"DELETE FROM {table_name}")
        try:
            connection.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table_name,))
        except sqlite3.Error:
            pass
        df.to_sql(table_name, connection, if_exists="append", index=False)
        connection.commit()

    return len(df)


def import_sample_data() -> dict[str, int]:
    """Import all bundled sample CSV files into their matching tables."""
    sample_dir = get_data_dir() / "sample"
    imported_counts: dict[str, int] = {}

    for table_name in TABLE_NAMES:
        csv_path = sample_dir / f"{table_name}.csv"
        imported_counts[table_name] = import_csv_to_table(csv_path, table_name)

    return imported_counts


def get_table_counts() -> dict[str, TableCount]:
    """Return row counts for known tables without failing on missing schema."""
    db_path = get_db_path()
    if not db_path.exists():
        return {table_name: "未初始化" for table_name in TABLE_NAMES}

    counts: dict[str, TableCount] = {}
    try:
        with get_connection() as connection:
            for table_name in TABLE_NAMES:
                try:
                    cursor = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
                    row = cursor.fetchone()
                    counts[table_name] = int(row["count"]) if row is not None else 0
                except sqlite3.Error:
                    counts[table_name] = "未初始化"
    except sqlite3.Error:
        return {table_name: "未初始化" for table_name in TABLE_NAMES}

    return counts


def get_recent_raw_files(conn: sqlite3.Connection, limit: int = 20) -> RecentRawFileRows:
    """Return recent raw file records, or None when the table is unavailable."""
    try:
        cursor = conn.execute(
            """
            SELECT
                id,
                file_name,
                data_type,
                year,
                source_name,
                source_url,
                saved_path,
                parse_status,
                parse_message,
                upload_time
            FROM raw_files
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        )
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return None


def get_table_row_counts(conn: sqlite3.Connection, table_names: list[str]) -> list[dict[str, object]]:
    """Return row counts for tables without failing when a table is missing."""
    rows: list[dict[str, object]] = []
    for table_name in table_names:
        if not table_name.replace("_", "").isalnum():
            rows.append({"table_name": table_name, "row_count": 0, "status": "missing"})
            continue

        try:
            cursor = conn.execute(f"SELECT COUNT(*) AS row_count FROM {table_name}")
            row = cursor.fetchone()
            row_count = int(row[0]) if row is not None else 0
            rows.append({"table_name": table_name, "row_count": row_count, "status": "exists"})
        except sqlite3.OperationalError:
            rows.append({"table_name": table_name, "row_count": 0, "status": "missing"})

    return rows
