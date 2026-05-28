import io
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from src.database import init_db
from src.data_importer import (
    create_raw_file_record,
    guess_field_mapping,
    import_dataframe_to_standard_table,
    normalize_empty_value,
    save_and_register_upload,
)


class NamedBytesIO(io.BytesIO):
    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name


@pytest.fixture()
def isolated_project_paths(tmp_path, monkeypatch):
    db_path = tmp_path / "db" / "test.db"
    data_dir = tmp_path / "data"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    init_db()
    return {"db_path": db_path, "data_dir": data_dir}


def _raw_file_id(saved_path: Path, data_type: str = "一分一段表") -> int:
    return create_raw_file_record(
        file_name=saved_path.name,
        file_type=saved_path.suffix.lstrip("."),
        data_type=data_type,
        year=2025,
        source_name="测试来源",
        source_url="https://example.com",
        saved_path=saved_path,
        parse_status="uploaded",
    )


def test_guess_field_mapping_matches_common_aliases():
    mapping = guess_field_mapping("admission_plans", ["院校代码", "院校名称", "专业代码", "专业名称", "计划数"])

    assert mapping["university_code"] == "院校代码"
    assert mapping["university_name"] == "院校名称"
    assert mapping["major_code"] == "专业代码"
    assert mapping["major_name"] == "专业名称"
    assert mapping["plan_count"] == "计划数"


def test_score_rank_missing_cumulative_count_is_key_field_missing(isolated_project_paths):
    raw_df = pd.DataFrame({"分数": [600], "科类": ["理科"]})
    raw_file_id = _raw_file_id(isolated_project_paths["data_dir"] / "score.csv")
    mapping = guess_field_mapping("score_rank", list(raw_df.columns))

    report = import_dataframe_to_standard_table(
        raw_file_id=raw_file_id,
        raw_df=raw_df,
        data_type="一分一段表",
        field_mapping=mapping,
        year=2025,
        province="内蒙古",
        category=None,
        source_file="score.csv",
        source_url="https://example.com",
    )

    assert report["imported_rows"] == 0
    assert report["missing_key_rows"] == 1


@pytest.mark.parametrize("value", ["-", "—", "", "暂无", "无"])
def test_normalize_empty_value_converts_common_empty_tokens(value):
    assert normalize_empty_value(value) is None


def test_pdf_upload_is_saved_only_and_not_imported(isolated_project_paths):
    uploaded_file = NamedBytesIO(b"%PDF-1.4\n", "policy.pdf")

    record = save_and_register_upload(
        uploaded_file,
        year=2025,
        data_type="招生章程",
        source_name="测试来源",
        source_url="https://example.com/policy.pdf",
    )

    assert record.parse_status == "saved_only"
    assert record.saved_path.exists()

    with sqlite3.connect(isolated_project_paths["db_path"]) as connection:
        raw_file = connection.execute(
            "SELECT parse_status, parse_message FROM raw_files WHERE id = ?",
            (record.id,),
        ).fetchone()
        charter_count = connection.execute("SELECT COUNT(*) FROM charter_constraints").fetchone()[0]

    assert raw_file[0] == "saved_only"
    assert "暂不执行复杂表格解析" in raw_file[1]
    assert charter_count == 0


def test_admission_plans_imports_with_common_aliases(isolated_project_paths):
    raw_df = pd.DataFrame(
        {
            "院校代码": ["10001"],
            "院校名称": ["测试大学"],
            "专业代码": ["080901"],
            "专业名称": ["计算机科学与技术"],
            "计划数": [12],
        }
    )
    raw_file_id = _raw_file_id(isolated_project_paths["data_dir"] / "plans.csv", data_type="招生计划")
    mapping = guess_field_mapping("admission_plans", list(raw_df.columns))

    report = import_dataframe_to_standard_table(
        raw_file_id=raw_file_id,
        raw_df=raw_df,
        data_type="招生计划",
        field_mapping=mapping,
        year=2025,
        province="内蒙古",
        category="理科",
        source_file="plans.csv",
        source_url="https://example.com/plans.csv",
    )

    assert report["imported_rows"] == 1
    assert report["missing_key_rows"] == 0

    with sqlite3.connect(isolated_project_paths["db_path"]) as connection:
        row = connection.execute(
            """
            SELECT university_code, university_name, major_code, major_name, plan_count, source_url
            FROM admission_plans
            """
        ).fetchone()

    assert row == ("10001", "测试大学", "080901", "计算机科学与技术", 12, "https://example.com/plans.csv")
