import os

import streamlit as st

from src.database import get_table_counts, init_db
from src.utils import (
    ensure_dirs,
    get_data_dir,
    get_db_path,
    get_llm_provider,
    is_llm_enabled,
)


APP_TITLE = "内蒙古高考志愿推荐智能体原型系统"


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🎓",
    layout="wide",
)

ensure_dirs()


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
        "当前阶段用于验证 Streamlit 页面、Docker 启动环境和基础项目结构。"
    )
    show_environment_info()


def show_data_import() -> None:
    st.title("数据导入")
    st.info("这里将用于导入院校、专业、分数线等基础数据。当前阶段仅保留页面占位。")

    if st.button("初始化数据库"):
        try:
            init_db()
            st.success("数据库初始化成功")
        except Exception as exc:
            st.error(f"数据库初始化失败：{exc}")


def show_recommendation() -> None:
    st.title("志愿推荐")
    st.info("这里将用于根据考生信息生成志愿推荐。当前阶段暂不实现推荐算法。")


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
    "志愿推荐": show_recommendation,
    "系统状态": show_system_status,
}


st.sidebar.title("导航")
selected_page = st.sidebar.radio("请选择页面", list(PAGES.keys()))
PAGES[selected_page]()
