import os

import streamlit as st


APP_TITLE = "内蒙古高考志愿推荐智能体原型系统"


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🎓",
    layout="wide",
)


def show_environment_info() -> None:
    st.subheader("当前环境信息")
    st.write("APP_ENV:", os.getenv("APP_ENV", "未设置"))
    st.write("DB_PATH:", os.getenv("DB_PATH", "./db/gaokao.db"))
    st.write("DATA_DIR:", os.getenv("DATA_DIR", "./data"))
    st.write("LLM_PROVIDER:", os.getenv("LLM_PROVIDER", "none"))


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


def show_recommendation() -> None:
    st.title("志愿推荐")
    st.info("这里将用于根据考生信息生成志愿推荐。当前阶段暂不实现推荐算法。")


def show_system_status() -> None:
    st.title("系统状态")
    st.info("这里将用于展示系统运行状态、数据连接状态和模型配置。")
    show_environment_info()


PAGES = {
    "首页": show_home,
    "数据导入": show_data_import,
    "志愿推荐": show_recommendation,
    "系统状态": show_system_status,
}


st.sidebar.title("导航")
selected_page = st.sidebar.radio("请选择页面", list(PAGES.keys()))
PAGES[selected_page]()
