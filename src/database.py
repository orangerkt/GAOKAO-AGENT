import sqlite3
from typing import Union

from src.utils import get_db_path


TABLE_NAMES = (
    "admission_records",
    "university_profiles",
    "major_profiles",
    "employment_profiles",
)

TableCount = Union[int, str]


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
            """
        )
        connection.commit()


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
