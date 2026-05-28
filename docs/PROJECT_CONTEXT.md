# PROJECT_CONTEXT

## 一、项目定位

本项目是一个高考志愿填报智能体。

目标：

基于：

* 高考分数
* 位次
* 历史录取数据
* 招生计划
* 专业信息
* 选科要求

为学生提供：

* 冲稳保推荐
* 志愿排序建议
* 推荐理由解释
* 政策问答

---

## 二、当前项目阶段

项目已经从：

“原型系统阶段”

进入：

“真实数据增强阶段”。

当前重点：

1. 数据可信
2. 数据结构化
3. 数据可追溯
4. 数据可计算

而不是优先追求花哨功能。

---

## 三、当前数据设计原则

### 结构化数据库

适合：

* 分数线
* 位次
* 招生计划
* 专业组
* 学费
* 学制
* 选科要求

### 向量库

适合：

* 招生章程
* 政策文件
* 院校介绍
* 专业介绍

---

## 四、当前项目目录结构

* src/
  核心代码

* data/
  原始数据与处理中数据

* db/
  SQLite数据库

* docs/
  项目上下文与设计文档

* tests/
  测试代码

---

## 五、当前主要待解决问题

1. 获取真实招生数据
2. Excel自动导入数据库
3. PDF结构化解析
4. 数据字段统一
5. 推荐逻辑设计
6. 建立位次换算逻辑

---

## 六、当前技术路线

当前倾向：

* SQLite
* pandas
* Docker
* Python
* 后续可能引入：
  FastAPI
  向量数据库
  Agent框架
  
## Docker 运行与开发约束

本项目要求以 Docker / docker-compose 作为主要运行和验收环境。

后续所有功能修改完成后，必须优先在 Docker 容器中验证，而不是只在本机 Python 环境中验证。

### 运行方式

项目根目录下使用：

```bash
docker compose up --build
```

或后台运行：

```bash
docker compose up -d --build
```

停止服务：

```bash
docker compose down
```

### 容器内测试方式

如果需要执行测试，应优先进入容器或通过 docker compose exec 执行，例如：

```bash
docker compose exec app pytest
```

如果 docker-compose.yml 中服务名不是 app，请根据实际服务名调整，例如 web、streamlit、gaokao-agent。

### 依赖管理规则

新增 Python 依赖时，必须写入 requirements.txt。

不要只在本机执行 pip install。

新增依赖后必须重新构建镜像：

```bash
docker compose up --build
```

### 数据库与文件持久化规则

SQLite 数据库文件、用户上传文件、真实数据原始文件必须通过项目目录或 Docker volume 持久化，不能只保存在容器临时层中。

重点目录：

```text
db/
data/uploads/
data/uploads/raw/
```

这些目录中的数据应在容器重启后仍然存在。

### 路径规则

代码中不要写死 Windows 绝对路径，例如：

```text
C:\Users\...
D:\...
F:\...
```

应统一使用相对路径或 pathlib，例如：

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "gaokao.db"
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
RAW_UPLOAD_DIR = BASE_DIR / "data" / "uploads" / "raw"
```

### Docker 环境下的验收标准

每次较大功能修改后，需要确认：

1. `docker compose up --build` 可以正常启动。
2. Streamlit 页面可以正常访问。
3. 原有推荐功能没有被破坏。
4. SQLite 数据库可以正常读写。
5. 上传文件可以保存到 data/uploads/ 或 data/uploads/raw/。
6. 容器重启后，数据库和上传文件仍然存在。
7. 如果新增依赖，requirements.txt、Dockerfile、docker-compose.yml 三者保持一致。
8. 不允许只在本机环境测试通过，却在 Docker 中无法运行。
