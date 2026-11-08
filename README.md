# 红脉智谱 RedTrace AI

**一师红色文化知识图谱与智能研学平台**

在线体验：<https://redtrace-ai.streamlit.app/>

> 2026-11-08 修正版：研学路线改为按「站数」规划（2 / 3 / 4 站），并修正了若干交互与部署细节。

## 项目简介

红脉智谱以湖南第一师范的红色文化资源为对象，把人物、旧址、事件、精神理念组织成可查询、可漫游的知识图谱，并提供问答、图谱探索和研学路线规划三个页面。

- **知识图谱**：48 个实体、77 条关系、23 种关系类型；支持实体详情、双向关系、两跳关联、搜索、类型筛选、缩放平移和两点最短路径。
- **问答**：支持实体名片、关系路径、邻居查询、图片直出、字段直查；没有配置大模型 API Key 时自动使用规则引擎，页面不会白屏。
- **研学路线**：5 条预置路线、20 个点位；支持按兴趣主题和 2/3/4 站生成定制路线，附地图、点位讲解、任务卡、测评和 docx 小结导出。
- **C 语言内核**：`graph.c` 实现邻接表、一跳邻居和 BFS 最短路径，Python 通过 `ctypes` 调用；云端由 `packages.txt` 安装 `build-essential` 后自动编译。

## 目录

```
app.py                 Streamlit 主入口
agent_llm.py           可选的大模型规划层（失败自动回退规则引擎）
c_core.py              C 内核的编译、加载与 ctypes 封装
graph.c                C 语言邻接表 / BFS
custom_route.py        按兴趣主题 + 站数的路线规划
ui_graph.py            知识图谱可视化
ui_campus_map.py       校区手绘地图
ui_map.py              Leaflet 地图
content/               路线、测评、时间轴数据
materials/             实体中英文资料
assets/                实体图片、背景图、地图
文档/                  依赖说明、工具调用记录
部署/                  局域网部署脚本与说明
```

## 本地运行

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

浏览器打开 <http://localhost:8501>。Windows 也可以直接双击 `启动红脉智谱.bat`。

## 公网部署

当前使用 Streamlit Community Cloud：

- Repository：`yee674/red`
- Branch：`main`
- Main file path：`app.py`
- Python 依赖：`requirements.txt`
- 系统依赖：`packages.txt`（`build-essential`，用于编译 `graph.c`）

在 Streamlit Cloud 的 App settings → Secrets 中可选配置：

```toml
LLM_API_KEY = "sk-..."
LLM_BASE_URL = "https://api.deepseek.com/v1"
LLM_MODEL = "deepseek-chat"
```

不配置时，问答自动使用规则引擎，功能仍可用。

## 数据与图片

实体、关系、资料来源记录在 `kg.json`；每个实体的详细资料在 `materials/`，配图在 `assets/`。图片来源与授权说明见 `kg.json` 中的 `image_credit` / `image_source` 字段。

## 说明

本仓库只包含可运行源码与运行所需资源，不包含课程报告中的个人材料（姓名、学号等）。
