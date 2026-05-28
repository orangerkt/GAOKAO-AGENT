import sqlite3

from src.database import get_recent_raw_files, get_table_row_counts


def test_get_recent_raw_files_returns_none_when_table_missing():
    connection = sqlite3.connect(":memory:")

    assert get_recent_raw_files(connection) is None


def test_get_table_row_counts_handles_existing_and_missing_tables():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE raw_files (id INTEGER PRIMARY KEY, file_name TEXT)")
    connection.execute("INSERT INTO raw_files (file_name) VALUES (?)", ("a.csv",))

    rows = get_table_row_counts(connection, ["raw_files", "score_rank"])

    assert rows == [
        {"table_name": "raw_files", "row_count": 1, "status": "exists"},
        {"table_name": "score_rank", "row_count": 0, "status": "missing"},
    ]


def test_get_recent_raw_files_returns_latest_rows():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE raw_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            data_type TEXT,
            year INTEGER,
            source_name TEXT,
            source_url TEXT,
            saved_path TEXT,
            parse_status TEXT,
            parse_message TEXT,
            upload_time TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT INTO raw_files (
            file_name, data_type, year, source_name, source_url,
            saved_path, parse_status, parse_message, upload_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("plans.csv", "招生计划", 2025, "测试来源", "https://example.com", "data/uploads/raw", "imported", None, "2026-01-01"),
    )

    rows = get_recent_raw_files(connection)

    assert rows is not None
    assert rows[0]["file_name"] == "plans.csv"
    assert rows[0]["parse_status"] == "imported"
