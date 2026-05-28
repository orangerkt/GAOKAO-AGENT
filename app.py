import os

import streamlit as st

from src.database import (
    TABLE_NAMES,
    get_connection,
    get_recent_raw_files,
    get_table_counts,
    get_table_row_counts,
    import_csv_to_table,
    import_sample_data,
    init_db,
)
from src.data_importer import (
    DATA_TYPE_TO_TABLE,
    PDF_SAVED_ONLY_MESSAGE,
    get_mappable_columns,
    get_target_table,
    guess_field_mapping,
    import_dataframe_to_standard_table,
    is_save_only_data_type,
    read_tabular_file,
    save_and_register_upload,
    update_raw_file_status,
)
from src.recommender import recommend_programs
from src.utils import (
    ensure_dirs,
    get_data_dir,
    get_db_path,
    get_llm_provider,
    is_llm_enabled,
)


APP_TITLE = "内蒙古高考志愿推荐智能体原型系统"

UPLOAD_LABELS = {
    "admission_records": "上传 admission_records.csv",
    "university_profiles": "上传 university_profiles.csv",
    "major_profiles": "上传 major_profiles.csv",
    "employment_profiles": "上传 employment_profiles.csv",
}

DISPLAY_COLUMNS = {
    "tier": "档位",
    "university_name": "院校",
    "major_name": "专业",
    "school_province": "院校省份",
    "city": "城市",
    "university_level": "院校层次",
    "min_score": "最低分",
    "min_rank": "最低位次",
    "plan_count": "计划数",
    "rank_diff": "位次差",
    "employment_rate": "就业率",
    "postgraduate_rate": "升学率",
    "recommended_graduate_rate": "保研/推免参考",
    "public_exam_fit_score": "考公适配度",
    "total_score": "综合分",
    "reason": "推荐理由",
    "risk_warning": "风险提示",
}

REAL_DATA_TYPE_OPTIONS = [
    "一分一段表",
    "批次线",
    "招生计划",
    "投档线",
    "录取结果",
    "选科要求",
    "招生章程",
    "就业质量报告",
    "保研/推免数据",
    "公务员岗位表",
]

STANDARD_DATA_TABLES = [
    "raw_files",
    "score_rank",
    "control_lines",
    "admission_plans",
    "admission_results",
    "subject_requirements",
    "charter_constraints",
    "civil_service_positions",
]


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🎓",
    layout="wide",
)

ensure_dirs()


def parse_multi_input(value: str) -> list[str]:
    normalized = value.replace("，", ",").replace("；", ",").replace(";", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def show_environment_info() -> None:
    st.subheader("当前环境信息")
    st.write("APP_ENV:", os.getenv("APP_ENV", "未设置"))
    st.write("DB_PATH:", get_db_path())
    st.write("DATA_DIR:", get_data_dir())
    st.write("LLM_PROVIDER:", get_llm_provider())


def show_table_counts() -> None:
    try:
        counts = get_table_counts()
    except Exception as exc:
        st.error(f"读取数据库状态失败：{exc}")
        return

    st.subheader("数据库表状态")
    st.write("admission_records 记录数:", counts.get("admission_records", "未初始化"))
    st.write("university_profiles 记录数:", counts.get("university_profiles", "未初始化"))
    st.write("major_profiles 记录数:", counts.get("major_profiles", "未初始化"))
    st.write("employment_profiles 记录数:", counts.get("employment_profiles", "未初始化"))


def show_home() -> None:
    st.title(APP_TITLE)
    st.write(
        "这是一个面向内蒙古高考志愿填报场景的原型系统。"
        "当前阶段用于验证 Streamlit 页面、Docker 启动环境、数据导入和最小推荐流程。"
    )
    show_environment_info()


def show_data_import() -> None:
    st.title("数据导入")
    st.info("这里用于初始化本地 SQLite 数据库，并导入示例或上传的 CSV 数据。")

    action_col_1, action_col_2 = st.columns(2)
    with action_col_1:
        if st.button("初始化数据库"):
            try:
                init_db()
                st.success("数据库初始化成功")
            except Exception as exc:
                st.error(f"数据库初始化失败：{exc}")

    with action_col_2:
        if st.button("导入示例数据"):
            try:
                imported_counts = import_sample_data()
                total_count = sum(imported_counts.values())
                st.success(f"示例数据导入成功，共导入 {total_count} 条记录。")
            except Exception as exc:
                st.error(f"示例数据导入失败：{exc}")

    st.subheader("上传 CSV")
    for table_name in TABLE_NAMES:
        uploaded_file = st.file_uploader(
            UPLOAD_LABELS[table_name],
            type=["csv"],
            key=f"upload_{table_name}",
        )
        if uploaded_file is not None and st.button(
            f"导入到 {table_name}",
            key=f"import_{table_name}",
        ):
            try:
                imported_count = import_csv_to_table(uploaded_file, table_name)
                st.success(f"{table_name} 导入成功，共导入 {imported_count} 条记录。")
            except Exception as exc:
                st.error(f"{table_name} 导入失败：{exc}")

    show_table_counts()


def _show_quality_report(report: dict) -> None:
    st.subheader("数据质量报告")
    st.write("目标表:", report.get("target_table") or "仅保存原始文件")
    st.write("总行数:", report.get("total_rows", 0))
    st.write("成功导入行数:", report.get("imported_rows", 0))
    st.write("缺失关键字段行数:", report.get("missing_key_rows", 0))
    st.write("重复行数:", report.get("duplicate_rows", 0))

    unrecognized_columns = report.get("unrecognized_columns") or []
    if unrecognized_columns:
        st.write("无法识别字段:", "、".join(unrecognized_columns))
    else:
        st.write("无法识别字段:", "无")

    suggestions = report.get("suggestions") or []
    if suggestions:
        st.write("建议人工检查项:")
        for suggestion in suggestions:
            st.write("-", suggestion)
    else:
        st.write("建议人工检查项: 暂无")


def _show_recent_raw_files() -> None:
    st.subheader("最近上传记录")
    try:
        with get_connection() as connection:
            rows = get_recent_raw_files(connection, limit=20)
    except Exception:
        rows = None

    if rows is None:
        st.info("raw_files 表尚未创建或暂无上传记录。")
        return
    if not rows:
        st.info("暂无上传记录。")
        return

    st.dataframe(rows, use_container_width=True, hide_index=True)


def _show_standard_table_stats() -> None:
    st.subheader("标准数据表统计")
    try:
        with get_connection() as connection:
            rows = get_table_row_counts(connection, STANDARD_DATA_TABLES)
    except Exception:
        rows = [
            {"table_name": table_name, "row_count": 0, "status": "missing"}
            for table_name in STANDARD_DATA_TABLES
        ]

    st.dataframe(rows, use_container_width=True, hide_index=True)


def _show_real_data_bottom_sections() -> None:
    _show_recent_raw_files()
    _show_standard_table_stats()


def show_real_data_import() -> None:
    st.title("真实数据导入")
    st.info("本页用于保存真实数据原始文件，并将 CSV / Excel 按字段映射结构化入库。PDF 当前仅保存登记。")
    init_db()

    with st.form("real_data_upload_form", clear_on_submit=False):
        uploaded_file = st.file_uploader(
            "上传文件",
            type=["csv", "xlsx", "xls", "pdf"],
            key="real_data_file",
        )
        col_1, col_2, col_3 = st.columns(3)
        with col_1:
            year = st.number_input("数据年份 year", min_value=2000, max_value=2100, value=2025, step=1)
            province = st.text_input("省份 province", value="内蒙古")
        with col_2:
            category = st.text_input("科类/类别 category（可为空）", value="")
            data_type = st.selectbox("数据类型 data_type", REAL_DATA_TYPE_OPTIONS)
        with col_3:
            source_name = st.text_input("来源名称 source_name", value="")
            source_url = st.text_input("来源链接 source_url", value="")

        save_submitted = st.form_submit_button("保存并预览")

    if save_submitted:
        if uploaded_file is None:
            st.warning("请先上传文件。")
        else:
            raw_file_id = None
            try:
                record = save_and_register_upload(
                    uploaded_file,
                    year=int(year),
                    data_type=data_type,
                    source_name=source_name.strip() or None,
                    source_url=source_url.strip() or None,
                )
                raw_file_id = record.id
                target_table = get_target_table(data_type)
                state = {
                    "raw_file_id": record.id,
                    "saved_path": str(record.saved_path),
                    "year": int(year),
                    "province": province.strip() or None,
                    "category": category.strip() or None,
                    "data_type": data_type,
                    "source_url": source_url.strip() or None,
                    "target_table": target_table,
                    "df": None,
                    "mapping": {},
                }

                if record.saved_path.suffix.lower() == ".pdf":
                    st.session_state["real_data_import_state"] = state
                    st.success(PDF_SAVED_ONLY_MESSAGE)
                elif is_save_only_data_type(data_type):
                    message = "该数据类型当前版本仅保存原始文件，不执行结构化入库。"
                    update_raw_file_status(record.id, "saved_only", message)
                    st.session_state["real_data_import_state"] = state
                    st.info(message)
                elif target_table is None:
                    message = "暂不支持该数据类型的结构化入库。"
                    update_raw_file_status(record.id, "failed", message)
                    st.session_state["real_data_import_state"] = state
                    st.error(message)
                else:
                    df = read_tabular_file(record.saved_path)
                    mapping = guess_field_mapping(target_table, list(df.columns))
                    state["df"] = df
                    state["mapping"] = mapping
                    st.session_state["real_data_import_state"] = state
                    st.success("文件已保存并读取成功，请检查预览和字段映射。")
            except Exception as exc:
                if raw_file_id is not None:
                    update_raw_file_status(int(raw_file_id), "failed", str(exc))
                st.error(f"保存或读取失败：{exc}")

    state = st.session_state.get("real_data_import_state")
    if state:
        st.subheader("上传记录")
        st.write("raw_files.id:", state["raw_file_id"])
        st.write("保存路径:", state["saved_path"])
        st.write("目标表:", state.get("target_table") or "仅保存原始文件")

        df = state.get("df")
        target_table = state["target_table"]

        if df is not None:
            st.subheader("前 20 行预览")
            st.dataframe(df.head(20), use_container_width=True)

        if df is not None and target_table:
            st.subheader("字段映射")
            st.caption(f"{state['data_type']} 将导入到 {DATA_TYPE_TO_TABLE[state['data_type']]}")
            raw_columns = [str(column) for column in df.columns]
            select_options = ["不映射", *raw_columns]
            current_mapping = state.get("mapping") or {}

            with st.form("real_data_mapping_form", clear_on_submit=False):
                selected_mapping: dict[str, str | None] = {}
                for target_column in get_mappable_columns(target_table):
                    guessed = current_mapping.get(target_column)
                    default_index = select_options.index(guessed) if guessed in select_options else 0
                    selected = st.selectbox(
                        target_column,
                        select_options,
                        index=default_index,
                        key=f"mapping_{state['raw_file_id']}_{target_column}",
                    )
                    selected_mapping[target_column] = None if selected == "不映射" else selected

                import_submitted = st.form_submit_button("校验并导入")

            if import_submitted:
                try:
                    report = import_dataframe_to_standard_table(
                        raw_file_id=int(state["raw_file_id"]),
                        raw_df=df,
                        data_type=state["data_type"],
                        field_mapping=selected_mapping,
                        year=state["year"],
                        province=state["province"],
                        category=state["category"],
                        source_file=state["saved_path"],
                        source_url=state["source_url"],
                    )
                    _show_quality_report(report)
                except Exception as exc:
                    update_raw_file_status(int(state["raw_file_id"]), "failed", str(exc))
                    st.error(f"导入失败：{exc}")

    _show_real_data_bottom_sections()


def show_recommendation() -> None:
    st.title("志愿推荐")
    st.info("推荐结果全部来自本地数据库。请先在“数据导入”页面初始化数据库并导入数据。")

    with st.form("recommendation_form"):
        col_1, col_2, col_3 = st.columns(3)
        with col_1:
            current_rank = st.number_input("考生位次", min_value=1, value=12000, step=100)
            category = st.selectbox("科类/类别", ["理科", "文科", "物理类", "历史类"])
            risk_preference = st.selectbox("风险偏好", ["均衡", "稳妥", "冲刺"])
        with col_2:
            preferred_provinces = st.text_input("意向省份", value="内蒙古自治区,辽宁省")
            preferred_cities = st.text_input("意向城市", value="呼和浩特,沈阳")
            top_k = st.number_input("返回数量", min_value=1, max_value=100, value=30, step=1)
        with col_3:
            preferred_university_levels = st.multiselect(
                "意向院校层次",
                ["985", "211", "双一流", "普通本科"],
                default=["211", "双一流"],
            )
            preferred_major_keywords = st.text_input("意向专业关键词", value="计算机,软件")

        submitted = st.form_submit_button("生成推荐")

    if submitted:
        user_profile = {
            "current_rank": int(current_rank),
            "category": category,
            "preferred_provinces": parse_multi_input(preferred_provinces),
            "preferred_cities": parse_multi_input(preferred_cities),
            "preferred_university_levels": preferred_university_levels,
            "preferred_major_keywords": parse_multi_input(preferred_major_keywords),
            "risk_preference": risk_preference,
            "top_k": int(top_k),
        }

        try:
            recommendations = recommend_programs(user_profile)
        except Exception as exc:
            st.error(f"生成推荐失败：{exc}")
            return

        if recommendations.empty:
            st.warning("数据库中暂时没有匹配的推荐结果。请确认已导入录取数据，并检查科类/类别是否匹配。")
            return

        display_df = recommendations.rename(columns=DISPLAY_COLUMNS)
        st.subheader("推荐结果")
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def show_system_status() -> None:
    db_path = get_db_path()
    data_dir = get_data_dir()
    llm_provider = get_llm_provider()

    st.title("系统状态")
    st.info("这里将用于展示系统运行状态、数据连接状态和模型配置。")

    st.subheader("基础配置")
    st.write("数据库路径:", db_path)
    st.write("数据目录:", data_dir)
    st.write("LLM_PROVIDER:", llm_provider)
    st.write("LLM 是否启用:", "是" if is_llm_enabled() else "否")
    st.write("数据库文件是否存在:", "是" if db_path.exists() else "否")

    show_table_counts()


PAGES = {
    "首页": show_home,
    "数据导入": show_data_import,
    "真实数据导入": show_real_data_import,
    "志愿推荐": show_recommendation,
    "系统状态": show_system_status,
}


st.sidebar.title("导航")
selected_page = st.sidebar.radio("请选择页面", list(PAGES.keys()))
PAGES[selected_page]()
