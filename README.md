---
title: 红脉智谱 RedTrace AI
emoji: 🚩
colorFrom: red
colorTo: gray
sdk: streamlit
sdk_version: 1.49.0
app_file: app.py
pinned: false
license: mit
---

# 🚩 红脉智谱 RedTrace AI

**一师红色文化知识图谱与智能研学平台**

- **关系挖掘**：33 个实体 / 47 条关系，C 语言邻接表 + BFS 最短路径算「两点怎么连」
- **人物追踪**：9 位一师人物的师友网络，可顺着关系一路点下去
- **AI 定制路线**：按兴趣主题 + 时长，自动排一条研学路线（地图打点 + 讲解 + 任务卡）

左侧可在 **问答 / 知识图谱 / 研学** 三页之间切换，右上角可切换 **中文 / English**。

> 本 Space 构建时会用 gcc 编译 `graph.c` 得到 `libgraph.so`；若宿主机没有 gcc，
> 程序自动退化为纯 Python 实现（`py_graph.py`），功能一致，侧边栏开发者面板会显示当前引擎。
