# -*- coding: utf-8 -*-
"""一师红色文化智能研学 —— Streamlit 前端

数据全部来自项目目录里的文件，改完保存即可自动刷新（见 README.md）：
    kg.json            实体与关系（结构）
    materials/<id>.md  每个实体的详细资料（支持 .zh.md / .en.md 双语）
    assets/<id>.jpg    实体配图（也可以写在 kg.json 的 "image" 字段里）
    assets/bg.jpg      页面背景图（换成自己的照片即可）

C 语言部分（graph.c / graph.dll）负责邻接表的存储与一跳邻居查询，
Python 通过 ctypes 调用，见 c_core.py。
"""
from __future__ import annotations

import base64
import difflib
import hashlib
import itertools
import json
import os
import random
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

import agent_llm
import flatpaths as fp
import qa_intent
import report as report_mod
import custom_route
import ui_graph
import ui_map
import ui_campus_map

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
MAPS = os.path.join(ASSETS, "maps")
MATERIALS = os.path.join(ROOT, "materials")
KG_PATH = os.path.join(ROOT, "kg.json")

# 开发说明类面板（怎么加资料、C 语言内核详情）默认不在界面显示，
# 需要时设置环境变量 RED_AGENT_DEV=1 再启动即可调出。
DEV_PANELS = os.environ.get("RED_AGENT_DEV", "").strip().lower() in ("1", "true", "yes", "on")

BG_CANDIDATES = ("bg.jpg", "bg.jpeg", "bg.png", "bg.webp",
                 "background.jpg", "background.png")
IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG", ".WEBP")

st.set_page_config(
    page_title="红脉智谱 RedTrace AI",
    page_icon="🚩",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 1. 多语言文案
# ============================================================
TEXT = {
    "zh": {
        "app_title": "红脉智谱",
        "badge": "湖南第一师范 · 红色文化知识图谱",
        "subtitle": "一师红色文化知识图谱与智能研学平台",
        "tags": "关系挖掘 · 人物追踪 · AI 定制路线",
        "language": "语言 / Language",
        "settings": "设置",
        "nav": "页面",
        "page_chat": "问答",
        "page_graph": "知识图谱",
        "page_study": "研学路线",
        "graph_hint": "点节点看详情与双向关系，关系行可以继续点；滚轮缩放、拖拽平移，试试「两点路径」。",
        "timeline_title": "一师求学时期大事时间轴",
        "view_entity": "选一个实体继续提问",
        "view_btn": "查看该实体",
        "choose_route": "选择研学路线",
        "duration": "建议时长",
        "pois_count": "个点位",
        "map_note": "手绘校园地图上的点位为示意位置；点击编号查看实拍图与讲解，滚轮缩放、拖拽平移。",
        "poi_list": "点位讲解",
        "open_entity": "查看实体卡片",
        "tasks": "研学任务卡",
        "quiz": "随堂测评",
        "quiz_new": "换一组题",
        "quiz_submit": "提交答案",
        "quiz_score": "得分",
        "quiz_need_all": "还有题目没有作答。",
        "quiz_all_right": "全部答对，厉害！",
        "export": "导出研学小结（docx）",
        "export_ready": "小结已生成，点下面的按钮下载。",
        "download": "下载小结",
        "correct": "正确答案",
        "no_image": "（暂无图片）",
        "custom_route": "AI 定制路线",
        "custom_hint": "选兴趣主题和时长，系统按实体类型匹配 + C 语言 BFS 跳数就近排序，为你生成一条路线。",
        "interest": "兴趣主题",
        "interest_person": "人物",
        "interest_place": "旧址",
        "interest_event": "事件",
        "interest_concept": "精神理念",
        "hours": "计划时长",
        "hours_unit": "小时",
        "start_from": "从哪开始",
        "generate": "生成我的路线",
        "custom_match": "主题匹配",
        "custom_hops": "距上一点 {n} 跳",
        "export_custom": "导出这条路线的小结",
        "data_status": "数据状态",
        "entities": "实体",
        "relations": "关系",
        "rel_types": "关系类型",
        "updated": "最后更新",
        "auto_refresh": "自动刷新（保存文件后自动更新页面）",
        "reload_now": "立即重新加载",
        "reloaded": "已重新加载最新数据。",
        "data_changed": "检测到数据文件变化，已自动更新。",
        "placeholder": "试试问：毛泽东入学年份、一师水井图片、冷水浴……",
        "welcome": "随便问一位人物、一处旧址或一个事件，我来把它们之间的关系理清楚。",
        "examples": "可以这样问",
        "not_found": "知识库里暂时没有这个实体。",
        "try_these": "试试这些：",
        "photo_none": "这个实体暂时没有配图。",
        "fact_none": "资料里还没有「{field}」这一条。",
        "fact_label": "{name} · {field}",
        "no_relations": "暂无关联关系。",
        "out_relations": "直接关联（本实体 → 其他实体）",
        "in_relations": "反向关联（其他实体 → 本实体）",
        "more": "还有 {n} 条",
        "two_hop": "间接关联（两跳路径）",
        "sources": "资料来源",
        "raw_c": "查看 C 层原始返回",
        "path_tool": "两点关系查询（C 语言 BFS 最短路径）",
        "path_from": "从",
        "path_to": "到",
        "path_btn": "查找关联路径",
        "path_hops": "{n} 跳",
        "path_same": "两个实体相同。",
        "path_none": "这两个实体之间没有连通路径。",
        "path_time": "C 语言 BFS 耗时",
        "path_time_py": "Python BFS 耗时",
        "engine": "内核引擎",
        "engine_c": "C 内核（graph.dll）",
        "engine_py": "Python 兜底（未编译 C）",
        "path_unsupported": "当前图形内核不支持路径查询。",
        "path_caption": "路径由 graph.c 中的 BFS 计算，反向边标为 ←。",
        "material_missing": "还没有为这个实体准备详细资料。在 `materials/{id}.md` 里写下内容即可自动显示。",
        "c_core": "C 语言内核",
        "c_core_info": "邻接表 + `query_neighbors()`，由 `graph.c` 编译为 `graph.dll` 后经 ctypes 调用，"
                       "查询实际发生在 C 里。数据变化时会自动加载一份新的 DLL 副本，无需重启。",
        "howto": "怎么加资料 / 图片",
        "howto_body": (
            "1. **加实体**：编辑 `kg.json` 的 `nodes`，写 `id`、`name`、`type`。\n"
            "2. **加关系**：在 `edges` 里写 `from`、`to`、`relation`。\n"
            "3. **加资料**：新建 `materials/<id>.md`（双语可建 `<id>.zh.md` / `<id>.en.md`）。\n"
            "4. **加图片**：把图片命名为 `<id>.jpg` 放进 `assets/`。\n\n"
            "保存后 3 秒内页面会自动更新，无需重启。"
        ),
        "type_unknown": "未分类",
        "reset_chat": "清空对话",
        "entity_removed": "这条消息关联的实体已从 kg.json 中删除。",
        "footer": "数据存放在 kg.json、materials/、assets/ 中，保存后页面会自动刷新。",
    },
    "en": {
        "app_title": "RedTrace AI",
        "badge": "Hunan First Normal School · Red Culture Knowledge Graph",
        "subtitle": "A knowledge graph and smart study platform for Hunan First Normal School's red culture",
        "tags": "Relation mining · Figure tracing · AI-planned routes",
        "language": "Language / 语言",
        "settings": "Settings",
        "nav": "Page",
        "page_chat": "Chat",
        "page_graph": "Knowledge graph",
        "page_study": "Routes",
        "graph_hint": "Click a node for details and two-way relations; relation rows are clickable too. Scroll to zoom, drag to pan, and try the shortest-path tool.",
        "timeline_title": "Timeline of the Hunan First Normal years",
        "view_entity": "Pick an entity to ask about",
        "view_btn": "Open this entity",
        "choose_route": "Choose a route",
        "duration": "Duration",
        "pois_count": "stops",
        "map_note": "Positions on the illustrated campus map are indicative; click a number for photos and notes, scroll to zoom, drag to pan.",
        "poi_list": "Stops and notes",
        "open_entity": "Open entity card",
        "tasks": "Route tasks",
        "quiz": "Quick quiz",
        "quiz_new": "New questions",
        "quiz_submit": "Submit answers",
        "quiz_score": "Score",
        "quiz_need_all": "Please answer every question.",
        "quiz_all_right": "All correct — well done!",
        "export": "Export study report (docx)",
        "export_ready": "Report ready — download it below.",
        "download": "Download report",
        "correct": "Correct answer",
        "no_image": "(no image yet)",
        "custom_route": "AI-planned route",
        "custom_hint": "Pick an interest and a duration; the route is planned by matching entity types and ordering stops by C-BFS hop distance.",
        "interest": "Interest",
        "interest_person": "People",
        "interest_place": "Sites",
        "interest_event": "Events",
        "interest_concept": "Ideas",
        "hours": "Duration",
        "hours_unit": "hours",
        "start_from": "Start from",
        "generate": "Plan my route",
        "custom_match": "theme match",
        "custom_hops": "{n} hop(s) from previous stop",
        "export_custom": "Export this route's report",
        "data_status": "Data status",
        "entities": "Entities",
        "relations": "Relations",
        "rel_types": "Relation types",
        "updated": "Last update",
        "auto_refresh": "Auto refresh (update the page when files are saved)",
        "reload_now": "Reload now",
        "reloaded": "Latest data loaded.",
        "data_changed": "Data files changed — page updated automatically.",
        "placeholder": "Try: Mao's enrolment year, a photo of the well, the cold water bath…",
        "welcome": "Ask about a person, a site or an event, and I will map out the relations behind it.",
        "examples": "Try asking",
        "not_found": "That entity is not in the knowledge base yet.",
        "try_these": "Did you mean:",
        "photo_none": "No photo available for this entity yet.",
        "fact_none": "No such field recorded yet: {field}.",
        "fact_label": "{name} · {field}",
        "no_relations": "No relations yet.",
        "out_relations": "Direct relations (this entity → others)",
        "in_relations": "Incoming relations (others → this entity)",
        "more": "+{n} more",
        "two_hop": "Indirect relations (two-hop paths)",
        "sources": "Sources",
        "raw_c": "Raw output from the C layer",
        "path_tool": "Path between two entities (C BFS shortest path)",
        "path_from": "From",
        "path_to": "To",
        "path_btn": "Find the path",
        "path_hops": "{n} hop(s)",
        "path_same": "The two entities are the same.",
        "path_none": "There is no connecting path between these two entities.",
        "path_time": "C BFS time",
        "path_time_py": "Python BFS time",
        "engine": "Engine",
        "engine_c": "C kernel (graph.dll)",
        "engine_py": "Python fallback (C not compiled)",
        "path_unsupported": "This graph engine does not support path queries.",
        "path_caption": "Computed by BFS in graph.c; a reversed edge is shown as ←.",
        "material_missing": "No detailed material yet. Add `materials/{id}.md` and it will appear here.",
        "c_core": "C core",
        "c_core_info": "Adjacency list + `query_neighbors()`, compiled from `graph.c` into `graph.dll` and "
                       "called through ctypes — the lookup happens in C. A fresh DLL copy is loaded "
                       "whenever the data changes, so no restart is needed.",
        "howto": "How to add material / images",
        "howto_body": (
            "1. **Entity** — edit `nodes` in `kg.json` (`id`, `name`, `type`).\n"
            "2. **Relation** — edit `edges` in `kg.json` (`from`, `to`, `relation`).\n"
            "3. **Material** — add `materials/<id>.md` (bilingual: `<id>.zh.md` / `<id>.en.md`).\n"
            "4. **Image** — put `<id>.jpg` into `assets/`.\n\n"
            "Save the file and the page refreshes itself within 3 seconds."
        ),
        "type_unknown": "Uncategorised",
        "reset_chat": "Clear chat",
        "entity_removed": "The entity behind this message was removed from kg.json.",
        "footer": "All data lives in kg.json, materials/ and assets/ — save a file and the page refreshes itself.",
    },
}

TYPE_LABELS = {
    "PERSON": ("人物", "Person"),
    "PLACE": ("旧址 · 场景", "Place"),
    "EVENT": ("事件", "Event"),
    "ORG": ("组织", "Organisation"),
    "CONCEPT": ("精神 · 理念", "Concept"),
    "WORK": ("文献 · 作品", "Work"),
}

PAGES = ("chat", "graph", "study")

# ============================================================
# 1.5 主题：原来的深色（dark，默认）+ 新增的亮色（light）
# ============================================================
THEME_DARK, THEME_LIGHT = "dark", "light"
THEMES = (THEME_DARK, THEME_LIGHT)          # 侧边栏里的先后顺序
THEME_TITLE = {"zh": "主题", "en": "Theme"}
THEME_LABELS = {
    "zh": {THEME_DARK: "🌙 深色模式", THEME_LIGHT: "☀️ 亮色模式"},
    "en": {THEME_DARK: "🌙 Dark mode", THEME_LIGHT: "☀️ Light mode"},
}


def current_theme() -> str:
    """当前主题，存在 session_state 里。

    没设置过时默认亮色（THEME_LIGHT）—— 打开就是亮色模式，
    需要深色的话在侧边栏「主题」里切换，选择会记在当前会话中。
    """
    return st.session_state.get("theme", THEME_LIGHT)


REL_LABELS = {
    "FOUNDED": ("创办", "Founded"),
    "CLASSMATE_OF": ("同学", "Classmate of"),
    "TEACHER_OF": ("老师", "Teacher of"),
    "STUDIED_AT": ("在此求学", "Studied at"),
    "PARTICIPATED_IN": ("参与", "Took part in"),
    "ADVOCATED": ("倡导", "Advocated"),
    "WROTE": ("撰写", "Wrote"),
    "LOCATED_IN": ("位于", "Located in"),
    "MEMBER_OF": ("成员", "Member of"),
    "PREDECESSOR_OF": ("前身", "Predecessor of"),
    "RELATED_TO": ("相关", "Related to"),
    "FRIEND_OF": ("挚友", "Friend of"),
    "PARTNER_OF": ("伴侣", "Partner of"),
    "PRACTICED_AT": ("在此实践", "Practised at"),
    "INFLUENCED": ("影响", "Influenced"),
    "MOTTO_OF": ("校训", "Motto of"),
    "EMBODIED_BY": ("体现", "Embodied by"),
    "USED_AS_TEXTBOOK": ("用作教材", "Used as textbook"),
    "PART_OF": ("属于", "Part of"),
    "LIVED_IN": ("居住", "Lived in"),
    "COMMEMORATES": ("纪念", "Commemorates"),
    "INSCRIBED": ("题写", "Inscribed"),
    "HELD_AT": ("举办于", "Held at"),
}


def rel_label(rel: str, lang: str) -> str:
    pair = REL_LABELS.get(rel)
    return pair[0] if lang == "zh" else pair[1] if pair else rel


def type_label(node_type: str, lang: str) -> str:
    pair = TYPE_LABELS.get(str(node_type).upper())
    if not pair:
        return TEXT[lang]["type_unknown"]
    return pair[0] if lang == "zh" else pair[1]


def display_name(node: dict, lang: str) -> str:
    """实体显示名：英文界面用 name_en（没写就回退中文名）。"""
    if lang == "en":
        return node.get("name_en") or node["name"]
    return node["name"]


def image_credit(node: dict, lang: str) -> str:
    if lang == "en":
        return node.get("image_credit_en") or node.get("image_credit") or ""
    return node.get("image_credit") or node.get("image_credit_en") or ""


def timestamp_text(mtime: float) -> str:
    """把 mtime 显示成「2026-10-24 13:24」而不是一串数字。"""
    try:
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError, OverflowError):
        return "-"


# ============================================================
# 2. 视觉样式
# ============================================================
def find_bg() -> str | None:
    for name in BG_CANDIDATES:
        hit = fp.resolve(ROOT, "assets", name)
        if hit:
            return hit
    return None


def bg_data_uri() -> str:
    """把背景图内联成 data URI，省去静态文件服务的路径问题。"""
    path = find_bg()
    if not path:
        return ""
    lower = path.lower()
    mime = "image/png" if lower.endswith(".png") else \
           "image/webp" if lower.endswith(".webp") else "image/jpeg"
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"


CSS = """
<style>
:root {
    /* 深色模式整体调亮：文字更亮、金色更暖、玻璃层更通透、描边更显眼 */
    --ink: #fdf8f5;
    --muted: #ecdcd6;
    --gold: #f6d9a4;
    --accent: #f2705a;
    --glass: rgba(104, 55, 55, 0.44);
    --line: rgba(246, 217, 164, 0.36);
}

/* ---------- 背景 ---------- */
[data-testid="stAppViewContainer"] {
    background-image:
        radial-gradient(120% 90% at 82% 0%, rgba(242, 112, 90, .24), transparent 55%),
        radial-gradient(90% 70% at 10% 100%, rgba(246, 217, 164, .15), transparent 60%),
        linear-gradient(180deg, rgba(46,21,23,.12) 0%, rgba(44,20,22,.20) 45%, rgba(40,18,20,.32) 100%),
        __BG__;
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
    background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
/* 只隐藏 Streamlit 自带的菜单 / 部署 / 状态图标，不要整个 stToolbar 都藏掉：
   侧边栏收起后，Streamlit 会在顶栏（stToolbar 里）放一个「展开侧边栏」按钮，
   以前的写法 display:none 会把它一起隐藏，于是侧边栏一收起来就再也点不回来。 */
#MainMenu, footer, [data-testid="stMainMenu"], [data-testid="stAppDeployButton"],
[data-testid="stStatusWidget"], [data-testid="stDecoration"] { display: none !important; }

/* 展开侧边栏按钮：做成深色背景上也看得清的胶囊按钮 */
[data-testid="stExpandSidebarButton"] {
    margin: .5rem 0 0 .5rem !important;
    padding: .2rem !important;
    border: 1px solid rgba(237,201,140,.48) !important;
    border-radius: 999px !important;
    background: rgba(112, 58, 58, .70) !important;
    box-shadow: 0 8px 22px rgba(0, 0, 0, .30);
    backdrop-filter: blur(8px);
    transition: all .18s ease;
}
[data-testid="stExpandSidebarButton"] svg { color: var(--gold) !important; fill: var(--gold) !important; }
[data-testid="stExpandSidebarButton"]:hover {
    border-color: var(--gold) !important;
    background: rgba(232, 192, 125, .2) !important;
    transform: translateY(-1px);
}
[data-testid="stMainBlockContainer"], .block-container {
    padding-top: 1.6rem;
    padding-bottom: 4.5rem;
    max-width: 1120px;
    margin: 0 auto;
}

/* ---------- 侧边栏 ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(122,62,60,.58), rgba(78,38,40,.62));
    border-right: 1px solid var(--line);
    backdrop-filter: blur(12px);
}
[data-testid="stSidebarContent"], [data-testid="stSidebarUserContent"] { background: transparent; }
[data-testid="stSidebar"] * { color: var(--ink); }
[data-testid="stSidebar"] .stButton > button { width: 100%; }

/* ---------- 文字 ---------- */
h1, h2, h3, h4 { color: var(--ink); letter-spacing: .01em; }
p, li, span, label { color: var(--ink); }
a { color: var(--gold) !important; text-decoration: none; border-bottom: 1px dotted rgba(232,192,125,.45); }
a:hover { color: #fff1cf !important; }
code { background: rgba(232,192,125,.12); color: #ffe9bd; border-radius: 4px; }

/* ---------- 顶部主视觉 ---------- */
.hero {
    position: relative;
    padding: 1.5rem 1.7rem 1.35rem;
    margin-bottom: 1.1rem;
    border-radius: 22px;
    border: 1px solid var(--line);
    background: linear-gradient(140deg, rgba(196, 74, 58, .60), rgba(96, 46, 48, .48) 62%);
    box-shadow: 0 20px 50px rgba(0, 0, 0, .26);
    backdrop-filter: blur(8px);
}
.hero .badge {
    display: inline-block;
    font-size: .74rem;
    letter-spacing: .16em;
    color: var(--gold);
    border: 1px solid rgba(232,192,125,.4);
    padding: .24rem .7rem;
    border-radius: 999px;
    background: rgba(232,192,125,.07);
}
.hero h1 { margin: .65rem 0 .45rem; font-size: clamp(1.5rem, 2.5vw, 2.1rem); line-height: 1.25; }
.hero h1 .h1-en {
    font-size: .48em;
    letter-spacing: .06em;
    color: var(--gold);
    font-weight: 500;
    margin-left: .25rem;
    vertical-align: middle;
    opacity: .92;
}
/* 标题右边的小图标：点一下打开湖南第一师范学院官网 */
.hero h1 .h1-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    margin-left: .3rem;
    border: 1px solid rgba(232, 192, 125, .45) !important;
    border-bottom: 1px solid rgba(232, 192, 125, .45) !important;
    border-radius: 999px;
    background: rgba(232, 192, 125, .12);
    vertical-align: middle;
    text-decoration: none !important;
    transition: all .18s ease;
}
.hero h1 .h1-link svg { width: .92rem; height: .92rem; display: block; }
.hero h1 .h1-link:hover {
    background: rgba(232, 192, 125, .26);
    border-color: var(--gold) !important;
    transform: translateY(-1px);
}
.hero p { margin: 0; color: var(--muted); font-size: .95rem; }
.hero-tags { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .7rem; }
.hero-tag {
    font-size: .76rem;
    color: #ffe7c4;
    border: 1px solid rgba(232,192,125,.38);
    background: rgba(232,192,125,.1);
    border-radius: 999px;
    padding: .2rem .65rem;
    letter-spacing: .02em;
}
.hero::after {
    content: "";
    position: absolute; inset: 0;
    border-radius: 22px;
    background: radial-gradient(120% 80% at 88% 10%, rgba(232,192,125,.16), transparent 60%);
    pointer-events: none;
}

/* ---------- 统计条 ---------- */
.stats { display: flex; flex-wrap: wrap; gap: .5rem; margin: 0 0 1.2rem; }
.stats .chip {
    font-size: .82rem;
    color: var(--muted);
    background: rgba(255,255,255,.13);
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: .3rem .8rem;
}
.stats .chip b { color: var(--gold); font-weight: 600; }

/* ---------- 聊天气泡 ---------- */
[data-testid="stChatMessage"] {
    background: var(--glass);
    border: 1px solid rgba(255,255,255,.1);
    border-radius: 18px;
    padding: .95rem 1.15rem;
    margin-bottom: .75rem;
    backdrop-filter: blur(8px);
    box-shadow: 0 10px 28px rgba(0,0,0,.25);
}
[data-testid="stChatMessage"] p { line-height: 1.75; }

/* ---------- 实体标题 ---------- */
.ent-head { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; margin-bottom: .35rem; }
.ent-name { font-size: 1.28rem; font-weight: 600; color: #fff6ec; letter-spacing: .02em; }
.ent-type {
    font-size: .74rem;
    color: var(--gold);
    border: 1px solid rgba(232,192,125,.4);
    background: rgba(232,192,125,.1);
    padding: .12rem .55rem;
    border-radius: 999px;
}
.section-title {
    font-size: .82rem;
    letter-spacing: .12em;
    color: var(--gold);
    text-transform: uppercase;
    margin: 1rem 0 .5rem;
    opacity: .9;
}

/* ---------- 两点路径 ---------- */
.path-head { display: flex; align-items: center; gap: .55rem; flex-wrap: wrap; margin-bottom: .2rem; }
.path-badge {
    font-size: .74rem;
    color: #1a0b0c;
    background: var(--gold);
    border-radius: 999px;
    padding: .12rem .6rem;
    font-weight: 600;
}
.pathline { display: flex; flex-wrap: wrap; align-items: center; gap: .45rem; margin: .65rem 0 .8rem; }
.pathline .pn {
    background: rgba(232,192,125,.14);
    border: 1px solid rgba(232,192,125,.42);
    color: #fff3e2;
    border-radius: 999px;
    padding: .3rem .8rem;
    font-size: .95rem;
    white-space: nowrap;
}
.pathline .pr { color: var(--gold); font-size: .8rem; letter-spacing: .03em; }

/* ---------- 按钮 ---------- */
.stButton > button {
    border-radius: 999px;
    border: 1px solid rgba(237,201,140,.36);
    background: rgba(255,255,255,.08);
    color: var(--ink);
    font-size: .88rem;
    padding: .32rem .85rem;
    transition: all .18s ease;
}
.stButton > button:hover {
    border-color: var(--gold);
    background: rgba(232,192,125,.16);
    color: #fff8ec;
    transform: translateY(-1px);
}

/* ---------- 输入框 ---------- */
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] { background: transparent !important; }
[data-testid="stChatInput"] {
    background: rgba(112, 58, 58, .62);
    border: 1px solid rgba(246,217,164,.42);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 12px 30px rgba(0,0,0,.32);
    backdrop-filter: blur(8px);
}
[data-testid="stChatInput"] div[data-baseweb="textarea"] { background: transparent; }
[data-testid="stChatInput"] textarea { color: var(--ink) !important; }
[data-testid="stChatInput"] textarea::placeholder { color: rgba(215,189,182,.65) !important; }

/* ---------- 其它组件 ---------- */
[data-testid="stExpander"] details {
    border: 1px solid var(--line);
    border-radius: 14px;
    background: rgba(255,255,255,.12);
}
[data-testid="stAlert"] { border-radius: 14px; }
hr { border-color: var(--line); }
.stRadio [role="radiogroup"] { gap: .35rem; }
img { border-radius: 14px; }

/* ---------- 新版页面组件（路线 / 图谱 / 调研） ---------- */
.page-head { margin: .2rem 0 1rem; }
.page-head h2 { margin: .15rem 0 .35rem; font-size: 1.5rem; }
.page-head p { margin: 0; color: var(--muted); font-size: .92rem; line-height: 1.7; }
.page-head .eyebrow {
    font-size: .72rem; letter-spacing: .16em; color: var(--gold);
    text-transform: uppercase; opacity: .95;
}

.study-hero {
    position: relative; overflow: hidden; border: 1px solid var(--line);
    border-radius: 22px; padding: 1.15rem 1.35rem 1.25rem; margin-bottom: 1rem;
    background:
        radial-gradient(120% 140% at 100% 0%, rgba(242,112,90,.28), transparent 55%),
        linear-gradient(135deg, rgba(124,62,62,.62), rgba(74,36,38,.54));
    box-shadow: 0 18px 40px rgba(0,0,0,.20);
}
.study-hero h2 { margin: .25rem 0 .4rem; font-size: 1.55rem; }
.study-hero .eyebrow { color: var(--gold); }
.study-hero p { margin: 0; color: var(--muted); font-size: .92rem; line-height: 1.7; max-width: 760px; }
.study-hero .hero-meta { display: flex; flex-wrap: wrap; gap: .45rem; margin-top: .8rem; }
.study-hero .hero-meta span {
    font-size: .75rem; color: #ffe7c4; border: 1px solid var(--line);
    background: rgba(237,201,140,.10); border-radius: 999px; padding: .22rem .65rem;
}

.route-card {
    position: relative; overflow: hidden; border-radius: 18px;
    border: 1px solid var(--line); min-height: 182px; margin-bottom: .5rem;
    background: #2a1517; box-shadow: 0 12px 26px rgba(0,0,0,.20);
    transition: transform .18s ease, border-color .18s ease;
}
.route-card:hover { transform: translateY(-2px); border-color: var(--gold); }
.route-card .rc-bg {
    position: absolute; inset: 0; background-size: cover; background-position: center;
    filter: saturate(.9);
}
.route-card .rc-shade {
    position: absolute; inset: 0;
    background: linear-gradient(180deg, rgba(14,6,7,.18), rgba(14,6,7,.88));
}
.route-card .rc-body { position: relative; padding: .8rem .9rem; display: flex; flex-direction: column; gap: .3rem; min-height: 182px; justify-content: flex-end; }
.route-card .rc-kicker { font-size: .68rem; letter-spacing: .14em; color: var(--gold); text-transform: uppercase; }
.route-card .rc-title { font-size: 1.08rem; font-weight: 700; color: #fff6ea; line-height: 1.35; }
.route-card .rc-sub { font-size: .76rem; color: #e3cbc3; line-height: 1.55; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; max-height: 2.7em; }
.route-card .rc-stats { display: flex; gap: .4rem; flex-wrap: wrap; margin-top: .15rem; }
.route-card .rc-stats span {
    font-size: .7rem; color: #ffe4bd; background: rgba(20,8,10,.55);
    border: 1px solid rgba(237,201,140,.30); border-radius: 999px; padding: .12rem .5rem;
}
.route-card.active { border-color: var(--gold); box-shadow: 0 0 0 2px rgba(237,201,140,.25), 0 14px 30px rgba(0,0,0,.26); }
.route-card.active::after {
    content: "✓"; position: absolute; right: 10px; top: 8px; z-index: 3;
    width: 22px; height: 22px; border-radius: 50%; background: var(--gold); color: #3a1114;
    font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center;
}

.route-brief {
    display: flex; flex-wrap: wrap; gap: .5rem; align-items: center;
    border: 1px solid var(--line); border-radius: 16px; padding: .65rem .9rem;
    background: var(--glass); margin: .35rem 0 .8rem;
}
.route-brief b { color: var(--gold); }
.route-brief .muted { color: var(--muted); font-size: .82rem; }
.route-brief .rc-tag {
    font-size: .72rem; color: var(--gold); border: 1px solid var(--line);
    background: rgba(237,201,140,.08); border-radius: 999px; padding: .14rem .55rem;
}

.stop-list { display: flex; flex-direction: column; gap: .45rem; }
.stop-row {
    display: flex; gap: .65rem; align-items: flex-start;
    border: 1px solid var(--line); border-radius: 14px; padding: .6rem .7rem;
    background: rgba(255,255,255,.12);
}
.stop-no {
    flex: 0 0 26px; height: 26px; border-radius: 50%;
    background: linear-gradient(135deg, #c44532, #e8c07d); color: #2a0d10;
    font-weight: 700; font-size: .8rem; display: flex; align-items: center; justify-content: center;
}
.stop-body { flex: 1; min-width: 0; }
.stop-name { font-size: .93rem; font-weight: 600; color: var(--ink); }
.stop-meta { font-size: .72rem; color: var(--muted); margin-top: .12rem; }
.stop-why { font-size: .76rem; color: var(--muted); margin-top: .25rem; line-height: 1.55; }

.step-card {
    border: 1px solid var(--line); border-radius: 16px; padding: .8rem .9rem .7rem;
    background: var(--glass); height: 100%;
}
.step-card .step-no { font-size: .7rem; letter-spacing: .12em; color: var(--gold); text-transform: uppercase; }
.step-card h4 { margin: .25rem 0 .35rem; font-size: 1rem; }
.step-card p { margin: 0; color: var(--muted); font-size: .78rem; line-height: 1.6; }

.progress-wrap { margin: .3rem 0 .7rem; }
.progress-wrap .plabel { display: flex; justify-content: space-between; font-size: .78rem; color: var(--muted); margin-bottom: .3rem; }
.progress-track { height: 9px; border-radius: 999px; background: rgba(255,255,255,.18); border: 1px solid var(--line); overflow: hidden; }
.progress-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #c44532, #e8c07d); transition: width .3s ease; }

.plan-hint {
    border: 1px dashed var(--line); border-radius: 14px; padding: .65rem .85rem;
    color: var(--muted); font-size: .82rem; line-height: 1.65;
    background: rgba(237,201,140,.05); margin: .3rem 0 .9rem;
}
.poi-chips { display: flex; flex-wrap: wrap; gap: .4rem; margin: .2rem 0 1rem; }
.poi-chip {
    font-size: .76rem; color: var(--ink); border: 1px solid var(--line);
    background: rgba(255,255,255,.13); border-radius: 999px; padding: .24rem .65rem;
}

.poi-grid-card { border: 1px solid var(--line); border-radius: 18px; overflow: hidden; background: var(--glass); height: 100%; }
.poi-grid-card .pc-img { height: 150px; background-size: cover; background-position: center; background-color: rgba(237,201,140,.08); }
.poi-grid-card .pc-body { padding: .7rem .85rem .85rem; }
.poi-grid-card .pc-title { font-size: .98rem; font-weight: 700; color: var(--ink); }
.poi-grid-card .pc-addr { font-size: .72rem; color: var(--muted); margin: .18rem 0 .4rem; }
.poi-grid-card .pc-intro { font-size: .79rem; color: var(--muted); line-height: 1.65; }

.gallery-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: .5rem; }
.gallery-grid figure { margin: 0; border-radius: 12px; overflow: hidden; border: 1px solid var(--line); background: rgba(255,255,255,.11); }
.gallery-grid img { width: 100%; height: 118px; object-fit: cover; display: block; }
.gallery-grid figcaption { font-size: .7rem; color: var(--muted); padding: .3rem .45rem; }
@media (max-width: 900px) { .gallery-grid { grid-template-columns: repeat(2, minmax(0,1fr)); } }

.fact-card { display: flex; align-items: baseline; gap: .75rem; flex-wrap: wrap; margin: .15rem 0 .1rem; }
.fact-value { font-size: 2.05rem; font-weight: 700; color: #edc98c; letter-spacing: .02em; line-height: 1.15; }
.fact-label { font-size: .82rem; color: var(--muted); }
</style>
"""


# ============================================================
# 2.5 亮色主题（☀️）
# 只是一层「覆盖样式」：上面 CSS 里的深色样式一行都没动，
# 只有当前主题是 light 时才会把它追加在后面，深色模式因此完全保持原样。
# ============================================================
LIGHT_CSS = """
<style>
html, body { color-scheme: light; }
:root {
    --ink: #1f2430;
    --muted: #5b6572;
    --gold: #a4611a;
    --accent: #c0392b;
    --glass: #ffffff;
    --line: rgba(31, 36, 48, 0.14);
}

/* ---------- 背景：亮色模式也用同一张底图，压一层暖白遮罩保证文字可读 ---------- */
[data-testid="stApp"], [data-testid="stAppViewContainer"] {
    background-color: #fbf7f5 !important;
}
[data-testid="stAppViewContainer"] {
    background-image:
        radial-gradient(120% 90% at 84% 0%, rgba(192, 57, 43, .16), transparent 52%),
        radial-gradient(90% 70% at 8% 100%, rgba(214, 122, 40, .13), transparent 58%),
        linear-gradient(180deg, rgba(255,252,250,.88) 0%, rgba(255,250,247,.91) 45%, rgba(253,245,241,.94) 100%),
        __BG_LIGHT__;
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
    background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stExpandSidebarButton"] {
    background: #ffffff !important;
    border-color: rgba(192, 57, 43, .28) !important;
    box-shadow: 0 6px 18px rgba(31, 36, 48, .12) !important;
}

/* ---------- 红色元素点缀（避免亮色模式太素） ---------- */
/* 顶部一条红色渐变细条 */
[data-testid="stAppViewContainer"]::before {
    content: ""; position: fixed; top: 0; left: 0; right: 0; height: 3px;
    z-index: 99999; pointer-events: none;
    background: linear-gradient(90deg, #b3271c 0%, #d8452f 36%, #e0813f 68%, #b3271c 100%);
}
/* 主视觉左侧红色竖条（写在后面的 .hero 规则里，避免被 border 简写覆盖） */
/* 区块小标题前加一条红色竖线 */
.section-title { position: relative; padding-left: .62rem !important; }
.section-title::before {
    content: ""; position: absolute; left: 0; top: .16em; bottom: .16em;
    width: 3px; border-radius: 2px; background: #c0392b;
}
/* 页面眉标用红色 */
.page-head .eyebrow, .study-hero .eyebrow { color: #c0392b !important; opacity: 1 !important; }
/* 分割线由灰变红渐变 */
hr {
    border: none !important; height: 1px !important;
    background: linear-gradient(90deg, #c0392b, rgba(192,57,43,.18) 45%, transparent) !important;
}
/* 聊天气泡左侧一道细红线（同样写在后面的气泡规则里） */

/* ---------- 侧边栏 ---------- */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e4e8ee !important;
    backdrop-filter: none !important;
}
/* 侧边栏顶部一道红色装饰条 */
[data-testid="stSidebar"] > div:first-child::before {
    content: ""; display: block; height: 3px; margin: 0 0 .75rem;
    border-radius: 999px;
    background: linear-gradient(90deg, #b3271c, #e0813f);
}
[data-testid="stSidebar"] * { color: var(--ink); }

/* ---------- 顶部主视觉 ---------- */
.hero {
    background: linear-gradient(140deg, #ffffff, #fdf0ea 62%) !important;
    border: 1px solid #f2ddd5 !important;
    border-left: 4px solid #c0392b !important;
    box-shadow: 0 12px 30px rgba(31, 36, 48, .07) !important;
    backdrop-filter: none !important;
}
.hero::after {
    background: radial-gradient(120% 80% at 88% 10%, rgba(192, 57, 43, .14), transparent 60%) !important;
}
/* 徽章改成红色，跟顶部红条呼应 */
.hero .badge {
    color: #c0392b !important;
    border-color: rgba(192, 57, 43, .32) !important;
    background: #fdeeeb !important;
}
.hero h1, .hero h1 .h1-en, .hero p { color: var(--ink) !important; }
.hero h1 .h1-en { color: #a4611a !important; opacity: 1 !important; }
.hero p { color: var(--muted) !important; }
.hero h1 .h1-link {
    background: #fdf6ea !important;
    border: 1px solid rgba(164, 97, 26, .35) !important;
}
.hero h1 .h1-link:hover { background: #f6ead6 !important; }
.hero-tag {
    color: #7a4a12 !important;
    border-color: rgba(164, 97, 26, .28) !important;
    background: #fdf6ea !important;
}

/* ---------- 统计条 / 聊天气泡 ---------- */
.stats .chip {
    background: #ffffff !important;
    border-color: #e4e8ee !important;
    color: var(--muted) !important;
}
.stats .chip b { color: #c0392b !important; }
[data-testid="stChatMessage"] {
    background: #ffffff !important;
    border: 1px solid #e8e2dd !important;
    border-left: 3px solid rgba(192, 57, 43, .55) !important;
    box-shadow: 0 8px 20px rgba(31, 36, 48, .06) !important;
    backdrop-filter: none !important;
}

/* ---------- 实体卡片 / 关系路径 ---------- */
.ent-name { color: var(--ink) !important; }
.ent-type {
    color: #c0392b !important;
    border-color: rgba(192, 57, 43, .3) !important;
    background: #fdeeeb !important;
}
.section-title { color: #a83a2c !important; opacity: 1 !important; }
.path-badge { background: var(--accent) !important; color: #fff !important; }
.pathline .pn {
    background: #ffffff !important;
    border-color: #dde2ea !important;
    color: var(--ink) !important;
}
.pathline .pr { color: #a4611a !important; }

/* ---------- 按钮 / 输入框 ---------- */
.stButton > button {
    background: #ffffff !important;
    border: 1px solid #dde2ea !important;
    color: var(--ink) !important;
    box-shadow: 0 1px 2px rgba(31, 36, 48, .05);
}
.stButton > button:hover {
    background: #fdf6ea !important;
    border-color: #a4611a !important;
    color: #7a4a12 !important;
}
[data-testid="stChatInput"] {
    background: #ffffff !important;
    border: 1px solid #dde2ea !important;
    box-shadow: 0 10px 24px rgba(31, 36, 48, .08) !important;
    backdrop-filter: none !important;
}
/* 输入框内层（textarea 容器）在深色主题里是 secondaryBackground，这里一并改白 */
[data-testid="stChatInput"] * { background-color: transparent !important; }
[data-testid="stChatInput"] > div { background-color: #ffffff !important; }
[data-testid="stChatInput"] textarea { color: var(--ink) !important; }
[data-testid="stChatInput"] textarea::placeholder { color: #98a1ad !important; }
[data-testid="stChatInputSubmitButton"] { background: #eef1f5 !important; }
[data-testid="stChatInputSubmitButton"] svg { color: #5b6572 !important; fill: #5b6572 !important; }
[data-testid="stBottom"] {
    background: linear-gradient(180deg, rgba(247, 248, 250, 0) 0%, #f7f8fa 55%) !important;
}

/* ---------- 折叠面板 / 提示 / 表格 / 代码 ---------- */
[data-testid="stExpander"] details {
    background: #ffffff !important;
    border: 1px solid #e4e8ee !important;
}
[data-testid="stExpanderDetails"] { border-color: #eef1f5 !important; }
[data-testid="stExpander"] summary { color: var(--ink) !important; }
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:focus,
[data-testid="stExpander"] summary:focus-visible,
[data-testid="stExpander"] summary:active,
[data-testid="stExpander"] details[open] > summary {
    background: #f7f8fa !important;
    color: #7a4a12 !important;
}
[data-testid="stVerticalBlock"] { border-color: #e6e9ef !important; }
[data-testid="stAlert"] {
    background: #ffffff !important;
    border: 1px solid #e4e8ee !important;
}
[data-testid="stAlert"] p { color: var(--ink) !important; }
[data-testid="stMarkdownContainer"] table { background: #ffffff !important; }
[data-testid="stMarkdownContainer"] th { background: #f2f4f8 !important; color: var(--ink) !important; }
[data-testid="stMarkdownContainer"] td { color: var(--ink) !important; }
[data-testid="stMarkdownContainer"] th,
[data-testid="stMarkdownContainer"] td { border-color: #e4e8ee !important; }
[data-testid="stMarkdownContainer"] pre,
[data-testid="stCode"] pre,
[data-testid="stCodeBlock"] pre {
    background: #f4f5f7 !important;
    color: #1f2430 !important;
    border: 1px solid #e4e8ee !important;
}
[data-testid="stMarkdownContainer"] code { background: #f0ece4 !important; color: #8a4b00 !important; }

/* ---------- 原生表单控件（底层仍是深色主题，这里改成浅色） ---------- */
[data-testid="stWidgetLabel"] p { color: var(--ink) !important; }
[data-testid="stRadioGroup"] p { color: var(--ink) !important; }
[data-testid="stSelectbox"] [role="group"] {
    background: #ffffff !important;
    border: 1px solid #dde2ea !important;
}
[data-testid="stSelectbox"] input[role="combobox"] { color: var(--ink) !important; }
[data-testid="stSelectbox"] input[role="combobox"]::placeholder { color: #98a1ad !important; }
[data-testid="stSelectbox"] button { color: #5b6572 !important; }
[data-testid="stSelectbox"] svg { color: #5b6572 !important; fill: #5b6572 !important; }

/* 下拉候选列表渲染在 body 上的 portal 里，默认是深色 */
[data-testid="stSelectboxVirtualDropdown"] {
    background: #ffffff !important;
    border: 1px solid #e4e8ee !important;
    box-shadow: 0 10px 26px rgba(31, 36, 48, .12) !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"] { color: var(--ink) !important; }
[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-focused="true"],
[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] {
    background: #fdf6ea !important;
    color: #7a4a12 !important;
}
[data-testid="portal"] [role="listbox"],
[data-testid="portal"] [data-baseweb="popover"],
[data-testid="portal"] ul { background: #ffffff !important; }
[data-testid="portal"] [role="option"] { color: var(--ink) !important; }
[data-testid="portal"] [role="option"]:hover,
[data-testid="portal"] [role="option"][aria-selected="true"] {
    background: #fdf6ea !important;
    color: #7a4a12 !important;
}

/* 单选圆圈：深色主题里是浅色描边，白底上会看不见 */
[data-testid="stRadioOption"]:not([data-selected="true"]) > div > div:first-child {
    background: #ffffff !important;
    border-color: #c3cad6 !important;
}
/* 选中项那层底色（深色主题里几乎看不见，白底上会偏红），调淡一些 */
[data-testid="stRadioGroup"] > div[data-selected="true"] {
    background: rgba(216, 69, 47, .07) !important;
    border-radius: 8px;
}
/* 开关（自动刷新）：关闭时是深灰轨道，白底上改成浅灰 */
[data-testid="stCheckbox"]:has(input[role="switch"]):not([data-selected="true"]) label > div:nth-of-type(1) {
    background-color: #d5dbe5 !important;
    border-color: #d5dbe5 !important;
}
/* 复选框（研学任务卡）：未勾选时是浅色描边，白底上看不见 */
[data-testid="stCheckbox"]:not(:has(input[role="switch"])):not([data-selected="true"]) label > div:nth-of-type(1) {
    background-color: #ffffff !important;
    border-color: #c3cad6 !important;
}
/* 下载按钮（导出的研学小结）跟普通按钮保持一致 */
[data-testid="stDownloadButton"] button,
.stDownloadButton button {
    background: #ffffff !important;
    border: 1px solid #dde2ea !important;
    color: var(--ink) !important;
}
[data-testid="stDownloadButton"] button:hover,
.stDownloadButton button:hover {
    background: #fdf6ea !important;
    border-color: #a4611a !important;
    color: #7a4a12 !important;
}

/* ---------- 其它 ---------- */
hr { border-color: #e4e8ee !important; }
[data-testid="stToast"] {
    background: #ffffff !important;
    color: var(--ink) !important;
    border: 1px solid #e4e8ee !important;
}

/* ---------- 新版组件在亮色主题下的覆盖 ---------- */
.study-hero {
    background:
        radial-gradient(120% 140% at 100% 0%, rgba(216,69,47,.10), transparent 55%),
        linear-gradient(135deg, #ffffff, #fdf5ef) !important;
    border-color: #eadfd6 !important;
    box-shadow: 0 14px 32px rgba(31,36,48,.07) !important;
}
.study-hero h2, .study-hero p { color: var(--ink) !important; }
.study-hero .hero-meta span {
    color: #7a4a12 !important; background: #fdf6ea !important; border-color: rgba(164,97,26,.25) !important;
}
.stop-row { background: #ffffff !important; border-color: #e4e8ee !important; }
.stop-name { color: var(--ink) !important; }
.progress-track { background: #edf0f5 !important; border-color: #e4e8ee !important; }
.page-head p, .step-card p, .poi-grid-card .pc-intro, .stop-meta, .stop-why { color: var(--muted) !important; }
.step-card, .poi-grid-card, .route-brief { background: #ffffff !important; border-color: #e4e8ee !important; }
.poi-grid-card .pc-img { background-color: #f2f4f8 !important; }
.plan-hint { background: #fdf8f0 !important; border-color: #e3d5c2 !important; color: #5b6572 !important; }
.poi-chip { background: #ffffff !important; border-color: #e4e8ee !important; color: #1f2430 !important; }
.fact-value { color: #8a3a1e !important; }
.fact-label { color: #5b6572 !important; }
</style>
"""

# 知识图谱 / 地图 / 时间轴是内联 HTML，颜色写死在组件里，
# 亮色主题下用这张表把深色换掉；深色主题直接返回原文，一个字都不动。
LIGHT_COLOR_SWAP = {
    "rgba(232,192,125,.65)": "rgba(164,97,26,.6)",
    "rgba(232,192,125,.55)": "rgba(164,97,26,.45)",
    "rgba(232,192,125,.45)": "rgba(164,97,26,.35)",
    "rgba(232,192,125,.4)": "rgba(164,97,26,.34)",
    "rgba(232,192,125,.35)": "rgba(164,97,26,.3)",
    "rgba(232,192,125,.25)": "rgba(164,97,26,.22)",
    "rgba(232,192,125,.2)": "rgba(164,97,26,.18)",
    "rgba(232,192,125,.18)": "rgba(164,97,26,.16)",
    "rgba(232,192,125,.16)": "rgba(164,97,26,.14)",
    "rgba(232,192,125,.12)": "rgba(164,97,26,.12)",
    "rgba(20,8,10,.94)": "#ffffff",
    "rgba(20,8,10,.85)": "#d5dbe4",
    "rgba(20,8,10,.9)": "#ffffff",
    "rgba(20,8,10,.8)": "#ffffff",
    "rgba(18,8,10,.35)": "rgba(255,255,255,.92)",
    "rgba(255,255,255,.045)": "#ffffff",
    "rgba(215,189,182,.4)": "rgba(31,36,48,.42)",
    "rgba(160,140,130,.35)": "rgba(31,36,48,.3)",
    "rgba(0,0,0,.5)": "rgba(31,36,48,.18)",
    "#e8c07d": "#a4611a",
    "#f5ebe6": "#1f2430",
    "#f7efe8": "#1f2430",
    "#d7bdb6": "#5b6572",
    "#cdb7af": "#5b6572",
    "#a08b83": "#5b6572",
    "#fff3d8": "#b06a12",
    "#14080a": "#ffffff",
    "#1d0f10": "#ffffff",
}


def themed_html(html: str) -> str:
    """亮色主题下把图表/地图里内联的深色配色换成浅色；深色主题原样返回。"""
    if current_theme() != THEME_LIGHT:
        return html
    for old in sorted(LIGHT_COLOR_SWAP, key=len, reverse=True):
        html = html.replace(old, LIGHT_COLOR_SWAP[old])
    return html


def inject_css() -> None:
    uri = bg_data_uri()
    # 两个主题共用同一张背景图，各自的遮罩颜色不同（深色压暗、亮色提亮）
    bg = f'url("{uri}")' if uri else \
        "linear-gradient(160deg, #6e2624 0%, #4a1719 55%, #381114 100%)"
    bg_light = f'url("{uri}")' if uri else \
        "linear-gradient(160deg, #fdf6f2 0%, #f7ece6 55%, #f2e4dc 100%)"
    css = CSS.replace("__BG__", bg)
    if current_theme() == THEME_LIGHT:
        css += LIGHT_CSS.replace("__BG_LIGHT__", bg_light)
    st.markdown(css, unsafe_allow_html=True)


# ============================================================
# 3. 数据加载（按文件指纹缓存 + 自动失效）
# ============================================================
def iter_material_files() -> list[str]:
    """支持 materials/ 目录，也支持平铺的 materials__*.md。"""
    return [path for _, path in fp.list_folder(ROOT, "materials", (".md",))]


def iter_asset_files() -> list[str]:
    return [path for _, path in fp.list_folder(ROOT, "assets", IMG_EXTS)]


def iter_content_files() -> list[str]:
    return [path for _, path in fp.list_folder(ROOT, "content", (".json",))]


def data_signature() -> str:
    """kg.json + materials + assets + content 的指纹；任何改动都会触发重新加载。"""
    h = hashlib.sha1()
    for path in [KG_PATH, *iter_material_files(), *iter_asset_files(), *iter_content_files()]:
        try:
            info = os.stat(path)
        except OSError:
            continue
        h.update(f"{os.path.basename(path)}|{info.st_mtime_ns}|{info.st_size};".encode())
    return h.hexdigest()[:16]


def build_index(kg: dict) -> dict:
    nodes = {n["id"]: n for n in kg["nodes"]}
    aliases: dict[str, str] = {}
    for nid, node in nodes.items():
        for alias in [nid, node["name"], *node.get("aliases", [])]:
            alias = str(alias).strip()
            if alias:
                aliases.setdefault(alias, nid)

    out_edges: dict[str, list[tuple[str, str]]] = {nid: [] for nid in nodes}
    in_edges: dict[str, list[tuple[str, str]]] = {nid: [] for nid in nodes}
    for e in kg["edges"]:
        if e["from"] in nodes and e["to"] in nodes:
            out_edges[e["from"]].append((e["to"], e["relation"]))
            in_edges[e["to"]].append((e["from"], e["relation"]))

    return {
        "nodes": nodes,
        "aliases": aliases,
        "out": out_edges,
        "in": in_edges,
        "rel_types": sorted({e["relation"] for e in kg["edges"]}),
        "kg": kg,
    }


def load_core(root: str):
    """按文件路径重新加载 c_core.py，然后调用 build_and_load(root)。

    为什么不用 `import c_core`：Streamlit 的热重跑只重新执行主脚本，
    已经 import 过的模块会一直留在进程里（sys.modules）。改了 c_core.py 之后，
    正在运行的服务里仍然是旧版函数，于是报
        build_and_load() takes 0 positional arguments but 1 was given
    这里每次都从磁盘按路径 exec 一份最新的 c_core.py，
    所以升级代码后只要刷新页面就会自动生效，不必重启服务。
    """
    import importlib.util
    import sys as _sys

    path = os.path.join(root, "c_core.py")
    if not os.path.exists(path):
        raise RuntimeError(f"找不到 c_core.py：{path}")

    name = "_c_core_runtime"          # 固定名字，重复 exec 不会在 sys.modules 里堆积
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 c_core.py：{path}")
    module = importlib.util.module_from_spec(spec)
    _sys.modules[name] = module
    spec.loader.exec_module(module)

    try:
        return module.build_and_load(root)
    except TypeError as exc:
        if "positional" in str(exc):
            raise RuntimeError(
                "运行中的服务仍在用旧版 c_core.py，且自动重载失败。\n"
                "请关闭终端（Ctrl+C）后重新运行 start.bat。"
            ) from exc
        raise


@st.cache_resource(show_spinner=False, max_entries=3)
def load_bundle(signature: str) -> dict:
    """签名变 → 重新读 kg.json 并重新加载 C 内核（新副本，全局状态是干净的）。"""
    with open(KG_PATH, encoding="utf-8") as f:
        kg = json.load(f)
    lib = load_core(ROOT)
    index = build_index(kg)
    index["lib"] = lib
    index["mtime"] = os.path.getmtime(KG_PATH)
    return index


def get_material(node_id: str, lang: str) -> tuple[str | None, str | None]:
    """materials/<id>.<lang>.md 优先，其次 materials/<id>.md。"""
    for name in (f"{node_id}.{lang}.md", f"{node_id}.md"):
        path = fp.resolve(ROOT, "materials", name)
        if path:
            with open(path, encoding="utf-8") as f:
                text = f.read().strip()
            if text:
                return text, name
    return None, None


def resolve_image(node: dict) -> str | None:
    """先看 kg.json 的 image 字段，再按 assets/<id>.<ext> 自动匹配。"""
    declared = str(node.get("image") or "").strip()
    if declared and not declared.lower().startswith("placeholder"):
        path = fp.resolve(ROOT, "assets", declared)
        if path:
            return path
    return fp.resolve_any(ROOT, "assets", node["id"], IMG_EXTS)


@st.cache_data(show_spinner=False, max_entries=160)
def _b64_file(path: str, mtime: float) -> str:
    """读文件并 base64；mtime 参与缓存键，图片替换后自动失效。"""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def thumb_uri(node: dict) -> str:
    """知识图谱详情卡用的缩略图（assets/_thumbs/<id>.jpg，没有就退回原图）。"""
    path = resolve_image(node)
    if not path:
        return ""
    stem = os.path.splitext(os.path.basename(path))[0]
    thumb = os.path.join(ASSETS, "_thumbs", stem + ".jpg")
    use = thumb if os.path.exists(thumb) else path
    try:
        return "data:image/jpeg;base64," + _b64_file(use, os.path.getmtime(use))
    except OSError:
        return ""


def map_uri(name: str) -> str:
    """手绘校园地图转 base64（campos 图放进 iframe 也能显示）。"""
    for candidate in (name, name + ".jpg", name + ".png"):
        path = os.path.join(MAPS, candidate)
        if os.path.exists(path):
            try:
                return "data:image/jpeg;base64," + _b64_file(path, os.path.getmtime(path))
            except OSError:
                return ""
    return ""


def find_entity(prompt: str, index: dict) -> str | None:
    """最长别名优先命中（避免「湖南第一师范旧址」被「第一师范旧址」抢走）。"""
    text = prompt.strip().lower()
    if not text:
        return None
    best_key, best_id = (-1, 0), None
    for alias, nid in index["aliases"].items():
        pos = text.find(alias.lower())
        if pos != -1:
            key = (len(alias), -pos)
            if key > best_key:
                best_key, best_id = key, nid
    return best_id


def find_all_entities(prompt: str, index: dict) -> list[str]:
    """（保留兼容）返回句中出现的全部实体。

    问答主流程已改用 qa_intent.match_entities()：那边做了「命中区间不重叠、
    长的优先」，能避免「一师水井」被「一师」抢走而误判成两点关系查询。
    这里保留给外部脚本调用。
    """
    text = prompt.strip().lower()
    hits: list[tuple[int, int, str]] = []
    for alias, nid in index["aliases"].items():
        pos = text.find(alias.lower())
        if pos != -1:
            hits.append((pos, -len(alias), nid))
    hits.sort()
    seen, out = set(), []
    for _, _, nid in hits:
        if nid not in seen:
            seen.add(nid)
            out.append(nid)
    return out


def two_hop_paths(node_id: str, index: dict, limit: int = 10) -> list[tuple[str, str]]:
    """本实体 → 中间实体 → 目标 的两跳路径（返回 id，显示时再按语言取名）。"""
    seen, paths = set(), []
    for mid, _ in index["out"].get(node_id, []):
        for target, _ in index["out"].get(mid, []):
            if target in (node_id, mid):
                continue
            key = (mid, target)
            if key in seen:
                continue
            seen.add(key)
            paths.append((mid, target))
    return paths[:limit]


# ============================================================
# 4. 界面组件
# ============================================================
def stats_html(index: dict, lang: str) -> str:
    t = TEXT[lang]
    return (
        f'<div class="stats">'
        f'<span class="chip">{t["entities"]} <b>{len(index["nodes"])}</b></span>'
        f'<span class="chip">{t["relations"]} <b>{len(index["kg"]["edges"])}</b></span>'
        f'<span class="chip">{t["rel_types"]} <b>{len(index["rel_types"])}</b></span>'
        f'</div>'
    )


def render_relation_chips(pairs, index, lang, prefix, columns=3, max_show=18) -> None:
    """关联实体做成一排可点的按钮，点一下就能继续追问。"""
    nodes = index["nodes"]
    shown = pairs[:max_show]
    for row in itertools.batched(shown, columns):
        cols = st.columns(len(row))
        for col, (target_id, rel) in zip(cols, row):
            with col:
                target_node = nodes[target_id]
                label = f"{display_name(target_node, lang)} · {rel_label(rel, lang)}"
                if st.button(label, key=f"{prefix}-{target_id}-{rel}", width="stretch"):
                    # 用英文名继续追问时，match 走 aliases（kg.json 里已含 name_en）
                    st.session_state["_pending"] = display_name(target_node, lang)
                    st.rerun()
    if len(pairs) > max_show:
        st.caption(TEXT[lang]["more"].format(n=len(pairs) - max_show))


def render_entity_card(entity_id: str, index: dict, lang: str, key_prefix: str) -> None:
    node = index["nodes"][entity_id]
    t = TEXT[lang]
    image_path = resolve_image(node)

    if image_path:
        left, right = st.columns([3, 1])
    else:
        left, right = st.container(), None

    with left:
        st.markdown(
            f'<div class="ent-head"><span class="ent-name">{display_name(node, lang)}</span>'
            f'<span class="ent-type">{type_label(node.get("type", ""), lang)}</span></div>',
            unsafe_allow_html=True,
        )
        material, _ = get_material(entity_id, lang)
        if material:
            st.markdown(material)
        elif node.get("desc"):
            desc = node.get("desc_en") or node["desc"] if lang == "en" else node["desc"]
            st.markdown(str(desc))
        else:
            st.caption(t["material_missing"].format(id=entity_id))

    if right is not None:
        with right:
            st.image(image_path, width="stretch",
                     caption=image_credit(node, lang) or None)

    out_pairs = index["out"].get(entity_id, [])
    in_pairs = index["in"].get(entity_id, [])

    if out_pairs:
        st.markdown(f'<div class="section-title">{t["out_relations"]}</div>',
                    unsafe_allow_html=True)
        render_relation_chips(out_pairs, index, lang, f"{key_prefix}-out")

    if in_pairs:
        st.markdown(f'<div class="section-title">{t["in_relations"]}</div>',
                    unsafe_allow_html=True)
        render_relation_chips(in_pairs, index, lang, f"{key_prefix}-in")

    if not out_pairs and not in_pairs:
        st.caption(t["no_relations"])

    paths = two_hop_paths(entity_id, index)
    if paths:
        with st.expander(f"{t['two_hop']} · {len(paths)}"):
            st.markdown("\n".join(
                f"- {display_name(node, lang)} → **{display_name(index['nodes'][mid], lang)}**"
                f" → **{display_name(index['nodes'][target], lang)}**"
                for mid, target in paths
            ))

    sources = node.get("sources") or []
    if sources:
        st.markdown(f'<div class="section-title">{t["sources"]}</div>', unsafe_allow_html=True)
        st.markdown("\n".join(f"- [{s}]({s})" for s in sources))

    lib = index.get("lib")
    if lib is not None:
        with st.expander(t["raw_c"]):
            count, raw = lib.query_raw(entity_id)
            st.caption(f'query_neighbors("{entity_id}", buf, 16384) → {count}')
            st.code(raw or "(empty)", language="text")


def make_path_message(a_id: str, b_id: str, index: dict) -> dict:
    """调用 C 语言的 BFS 求两点最短路径，顺带记录 C 侧耗时。"""
    msg = {"role": "assistant", "kind": "path", "from": a_id, "to": b_id,
           "hops": -2, "steps": [], "elapsed_us": 0.0}
    lib = index.get("lib")
    if lib is None:
        return msg
    started = time.perf_counter()
    hops, steps = lib.find_path(a_id, b_id)
    msg["elapsed_us"] = (time.perf_counter() - started) * 1e6
    msg["hops"] = hops
    msg["steps"] = steps
    return msg


def render_path_card(msg: dict, index: dict, lang: str) -> None:
    """把 BFS 结果画成「实体 —关系→ 实体」的链路。"""
    t = TEXT[lang]
    nodes = index["nodes"]
    if msg.get("from") not in nodes or msg.get("to") not in nodes:
        st.warning(t["entity_removed"])
        return

    a = display_name(nodes[msg["from"]], lang)
    b = display_name(nodes[msg["to"]], lang)
    hops = msg.get("hops", -2)

    if hops == -2:
        st.markdown(f"**{a}** ↔ **{b}**")
        st.caption(t["path_unsupported"])
        return
    if hops < 0:
        st.markdown(f"**{a}** ↔ **{b}**")
        st.caption(t["path_none"])
        return
    if hops == 0:
        st.markdown(f"**{a}**")
        st.caption(t["path_same"])
        return

    chips = [f'<span class="pn">{a}</span>']
    for _, rel, nxt, reversed_ in msg["steps"]:
        label = rel_label(rel, lang)
        arrow = f"← {label} —" if reversed_ else f"— {label} →"
        chips.append(f'<span class="pr">{arrow}</span>')
        chips.append(f'<span class="pn">{display_name(nodes[nxt], lang)}</span>')

    st.markdown(
        f'<div class="path-head"><span class="path-badge">{t["path_hops"].format(n=hops)}</span>'
        f'<span class="ent-name">{a}</span><span class="pr">↔</span>'
        f'<span class="ent-name">{b}</span></div>'
        f'<div class="pathline">{"".join(chips)}</div>',
        unsafe_allow_html=True,
    )
    engine = getattr(index.get("lib"), "engine", "c")
    time_label = t["path_time"] if engine == "c" else t["path_time_py"]
    st.caption(f'{time_label} {msg.get("elapsed_us", 0):.2f} µs · {t["path_caption"]}')


def render_photo_card(msg: dict, index: dict, lang: str) -> None:
    """只回一张图：问「XX 图片 / 照片」时用。

    刻意不带标题和关系，只留图片本身 + 一行图片署名（版权要求）。
    如果连署名都不想要，删掉 st.image 的 caption 参数即可。
    """
    t = TEXT[lang]
    node = index["nodes"].get(msg.get("entity_id", ""))
    if node is None:
        st.warning(t["entity_removed"])
        return
    path = resolve_image(node)
    if not path:
        st.markdown(f'**{display_name(node, lang)}**')
        st.caption(t["photo_none"])
        return
    st.image(path, width=460, caption=image_credit(node, lang) or None)


def render_fact_card(msg: dict, index: dict, lang: str) -> None:
    """只回一个字段值：问「毛泽东入学年份」就给 1913，不铺整张名片。

    字段全部来自 kg.json 的 facts，查不到就说没有，不会编。
    """
    t = TEXT[lang]
    node = index["nodes"].get(msg.get("entity_id", ""))
    if node is None:
        st.warning(t["entity_removed"])
        return

    field = msg.get("field", "")
    fact = next((f for f in node.get("facts") or [] if f.get("key") == field), None)
    if fact is None:
        st.caption(t["fact_none"].format(field=field))
        return

    en = lang == "en"
    value = fact.get("value_en") if en and fact.get("value_en") else fact.get("value")
    label = fact.get("key_en") if en and fact.get("key_en") else field
    note = fact.get("note_en") if en and fact.get("note_en") else fact.get("note")

    st.markdown(
        f'<div class="fact-card"><span class="fact-value">{value}</span>'
        f'<span class="fact-label">'
        f'{t["fact_label"].format(name=display_name(node, lang), field=label)}</span></div>',
        unsafe_allow_html=True,
    )
    if note:
        st.caption(note)


def render_message(msg: dict, index: dict, lang: str, idx: int) -> None:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        elif msg.get("kind") == "entity":
            # 实体可能已经从 kg.json 里删掉了，历史消息要优雅降级而不是整页报错
            if msg["entity_id"] in index["nodes"]:
                render_entity_card(msg["entity_id"], index, lang, f"m{idx}")
            else:
                st.warning(TEXT[lang]["entity_removed"])
        elif msg.get("kind") == "path":
            render_path_card(msg, index, lang)
        elif msg.get("kind") == "photo":
            render_photo_card(msg, index, lang)
        elif msg.get("kind") == "fact":
            render_fact_card(msg, index, lang)
        elif msg.get("kind") == "route":
            render_route_card(msg, index, lang)
        else:
            st.markdown(msg.get("text", ""))
            for name in msg.get("suggestions", []):
                if st.button(name, key=f"sug-{idx}-{name}"):
                    st.session_state["_pending"] = name
                    st.rerun()
        if msg["role"] == "assistant":
            render_agent_tag(msg.get("agent"), lang)


def answer_rule(prompt: str, index: dict, lang: str) -> dict:
    """规则引擎：先判意图，再挑工具执行。

    意图由 qa_intent.detect() 给出，四种走法：
        photo  「一师水井图片」           → 只回一张图，不铺整张卡
        fact   「毛泽东入学年份」         → 只回这个字段的值
        path   「毛泽东和杨昌济什么关系」 → 交给 C 的 BFS 求最短路
        entity 「毛泽东」                 → 完整实体名片

    没有配置大模型、或模型调用/校验失败时，由 answer() 回退到这里，
    保证离线、断网、没填 Key 的机器上核心算法依然可用。
    """
    t = TEXT[lang]
    plan = qa_intent.detect(prompt, index, lang)
    intent = plan.get("intent")

    if intent == "photo":
        return {"role": "assistant", "kind": "photo", "entity_id": plan["entity"]}
    if intent == "fact":
        return {"role": "assistant", "kind": "fact",
                "entity_id": plan["entity"], "field": plan.get("field", "")}
    if intent == "path":
        return make_path_message(plan["a"], plan["b"], index)
    if intent == "entity":
        return {"role": "assistant", "kind": "entity", "entity_id": plan["entity"]}

    entity_id = find_entity(prompt, index)
    if entity_id:
        return {"role": "assistant", "kind": "entity", "entity_id": entity_id}

    display = [display_name(n, lang) for n in index["kg"]["nodes"]]
    close = difflib.get_close_matches(prompt.strip(), display, n=3, cutoff=0.3)
    text = f"⚠️ {t['not_found']}"
    if close:
        text += "\n\n" + t["try_these"] + " " + " / ".join(f"**{c}**" for c in close)
    return {"role": "assistant", "kind": "notice", "text": text, "suggestions": close}


# ============================================================
# 4.1 智能体：大模型规划 + 确定性工具执行（失败自动回退）
# ============================================================
AGENT_TEXT = {
    "zh": {
        "llm_tag": "🧠 大模型规划 · {model} · {n} 次调用 · 参数校验通过 · 工具：{tool} · {ms:.0f} ms",
        "rule_tag": "⚙️ 规则引擎（{why}）· 工具：{tool} · {ms:.0f} ms",
        "why_nokey": "未配置 API Key，走离线规则",
        "why_fail": "模型不可用或参数不合法，已回退",
        "tool_path": "C-BFS 最短路",
        "tool_entity": "邻接表一跳邻居",
        "tool_route": "贪心最近邻路线",
        "tool_photo": "实体配图直出",
        "tool_fact": "字段直查",
        "tool_rule": "别名最长匹配",
        "log": "调用记录",
        "log_hint": "每次问答的模型、参数校验、实际调用的工具与耗时，可直接导出作为验收证据。",
        "log_empty": "还没有调用记录。",
        "log_download": "下载调用记录 JSON",
        "route_title": "定制路线",
        "route_hours": "{h} 小时",
        "route_hops": "距上一点 {n} 跳",
        "route_match": "主题匹配",
    },
    "en": {
        "llm_tag": "🧠 LLM planner · {model} · {n} call(s) · params validated · tool: {tool} · {ms:.0f} ms",
        "rule_tag": "⚙️ Rule engine ({why}) · tool: {tool} · {ms:.0f} ms",
        "why_nokey": "no API key, offline rules",
        "why_fail": "model unavailable or params invalid, fell back",
        "tool_path": "C BFS shortest path",
        "tool_entity": "adjacency 1-hop neighbours",
        "tool_route": "greedy nearest neighbour route",
        "tool_photo": "entity photo only",
        "tool_fact": "field lookup",
        "tool_rule": "longest-alias match",
        "log": "Tool-call log",
        "log_hint": "Model, param validation, tool used and latency per turn; exportable as evidence.",
        "log_empty": "No calls recorded yet.",
        "log_download": "Download call log (JSON)",
        "route_title": "Custom route",
        "route_hours": "{h} h",
        "route_hops": "{n} hop(s) from previous stop",
        "route_match": "theme match",
    },
}


def _tool_route(params: dict, index: dict, lang: str) -> dict | None:
    """工具三：按兴趣主题 + 时长生成路线（跳数来自 C 的 BFS，排序用贪心最近邻）。"""
    pois = _all_pois(lang, index)
    if not pois:
        return None
    result = custom_route.generate(index, pois, params["kind"], params["hours"], params["start"])
    items = [{"entity": it["poi"]["entity"], "dist": it["dist"], "match": it["match"]}
             for it in result["items"]]
    if not items:
        return None
    return {"role": "assistant", "kind": "route", "hours": params["hours"],
            "kind_type": params["kind"], "items": items}


def _llm_dispatch(params: dict, index: dict, lang: str) -> tuple[dict | None, str]:
    """把校验过的参数分派给工具。返回 (消息, 工具名)。"""
    intent = params["intent"]
    if intent == "path":
        return make_path_message(params["a"], params["b"], index), "path"
    if intent in ("entity", "neighbors"):
        return {"role": "assistant", "kind": "entity", "entity_id": params["entity"]}, "entity"
    if intent == "photo":
        return {"role": "assistant", "kind": "photo", "entity_id": params["entity"]}, "photo"
    if intent == "fact":
        return {"role": "assistant", "kind": "fact", "entity_id": params["entity"],
                "field": params.get("field", "")}, "fact"
    if intent == "route":
        return _tool_route(params, index, lang), "route"
    return None, "unknown"


def _log_call(prompt: str, meta: dict, tool: str) -> None:
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "prompt": prompt,
        "engine": meta.get("engine", "rule"),
        "model": meta.get("model", ""),
        "intent": meta.get("intent", ""),
        "params": meta.get("params", {}),
        "tool": tool,
        "validated": bool(meta.get("validated")),
        "attempts": meta.get("attempts", 0),
        "repaired": bool(meta.get("repaired")),
        "elapsed_ms": round(float(meta.get("elapsed_ms", 0.0)), 2),
        "error": meta.get("error", ""),
    }
    st.session_state.setdefault("agent_log", []).append(entry)


def render_agent_tag(meta: dict, lang: str) -> None:
    """在回答下面标一行「谁规划的、校验过没有、调了哪个工具、多久」。"""
    if not meta:
        return
    txt = AGENT_TEXT[lang]
    tool = txt.get("tool_" + str(meta.get("tool", "")), meta.get("tool", ""))
    if meta.get("engine") == "llm" and meta.get("validated"):
        line = txt["llm_tag"].format(model=meta.get("model", ""), n=meta.get("attempts", 1),
                                     tool=tool, ms=float(meta.get("elapsed_ms", 0.0)))
    else:
        why = txt["why_nokey"] if "API Key" in str(meta.get("error", "")) else txt["why_fail"]
        line = txt["rule_tag"].format(why=why, tool=tool,
                                      ms=float(meta.get("elapsed_ms", 0.0)))
    st.caption(line)


def render_route_card(msg: dict, index: dict, lang: str) -> None:
    txt = AGENT_TEXT[lang]
    st.markdown(
        f"**✨ {txt['route_title']} · {txt['route_hours'].format(h=msg['hours'])} · "
        f"{len(msg['items'])} {('点位' if lang == 'zh' else 'stops')}**"
    )
    for n, it in enumerate(msg["items"], 1):
        node = index["nodes"].get(it["entity"], {})
        name = display_name(node, lang) if node else it["entity"]
        badge = f"　`{txt['route_match']}`" if it.get("match") else ""
        st.markdown(f"{n}. **{name}** — {txt['route_hops'].format(n=it['dist'])}{badge}")


def answer(prompt: str, index: dict, lang: str) -> dict:
    """智能体总入口：先让大模型理解需求并给出参数，校验通过才调工具。

    三条铁律：
      1. 模型只解析、不算数，结果以工具返回值为准；
      2. 参数必须过白名单（实体要在图谱里、时长只能 2/3/4）；
      3. 任何一步失败都回退规则引擎，聊天不会因为模型坏了而不可用。
    """
    meta: dict = {"engine": "rule", "model": "", "elapsed_ms": 0.0, "attempts": 0,
                  "validated": False, "repaired": False, "error": "未配置 LLM_API_KEY"}

    if agent_llm.available():
        result = agent_llm.plan(prompt, index, lang)
        meta = dict(result["meta"])
        if result["ok"]:
            msg, tool = _llm_dispatch(result["params"], index, lang)
            if msg is not None:
                meta.update({"tool": tool, "params": result["params"],
                             "intent": result["params"]["intent"]})
                msg["agent"] = meta
                _log_call(prompt, meta, tool)
                return msg
            meta["error"] = "参数合法但没有可执行的工具"

    fallback = {"engine": "rule", "model": meta.get("model", ""),
                "elapsed_ms": meta.get("elapsed_ms", 0.0), "attempts": meta.get("attempts", 0),
                "validated": False, "repaired": False, "error": meta.get("error", ""),
                "tool": "rule"}
    msg = answer_rule(prompt, index, lang)
    msg["agent"] = fallback
    _log_call(prompt, fallback, "rule")
    return msg


def render_agent_log(lang: str) -> None:
    """调用记录面板：验收时直接展示「真实工具调用」的证据。"""
    txt = AGENT_TEXT[lang]
    entries = st.session_state.get("agent_log", [])
    with st.expander(f"🧾 {txt['log']}（{len(entries)}）", expanded=False):
        st.caption(txt["log_hint"])
        if not entries:
            st.caption(txt["log_empty"])
            return
        st.dataframe(
            [{"时间": e["time"], "引擎": e["engine"], "模型": e["model"],
              "意图": e["intent"] or "-", "工具": e["tool"],
              "参数校验": "通过" if e["validated"] else "回退",
              "耗时(ms)": e["elapsed_ms"], "输入": e["prompt"][:28]}
             for e in entries[-20:]],
            width="stretch", hide_index=True,
        )
        st.download_button(
            txt["log_download"],
            data=json.dumps(entries, ensure_ascii=False, indent=2),
            file_name="agent_call_log.json",
            mime="application/json",
            key="agent-log-download",
        )


def sidebar(index: dict, lang: str) -> bool:
    t = TEXT[lang]
    with st.sidebar:
        st.markdown(f"### ⚙️ {t['settings']}")

        options = ["zh", "en"]
        labels = {"zh": "中文", "en": "English"}
        picked = st.radio(
            t["language"], options,
            index=options.index(st.session_state.lang),
            format_func=lambda code: labels[code],
            horizontal=True, key="lang_choice",
        )
        if picked != st.session_state.lang:
            st.session_state.lang = picked
            st.rerun()

        # ---- 主题切换（🌙 原有深色 / ☀️ 亮色）----
        picked_theme = st.radio(
            THEME_TITLE[lang], THEMES,
            index=THEMES.index(current_theme()),
            format_func=lambda code: THEME_LABELS[lang][code],
            horizontal=True, key="theme_choice",
        )
        if picked_theme != current_theme():
            st.session_state.theme = picked_theme
            st.rerun()

        st.divider()
        st.markdown(f"#### 🧭 {t['nav']}")
        page_labels = {"chat": f"💬 {t['page_chat']}",
                       "graph": f"🕸️ {t['page_graph']}",
                       "study": f"🎒 {t['page_study']}"}
        page = st.radio(
            t["nav"], list(PAGES), index=list(PAGES).index(st.session_state.page),
            format_func=lambda code: page_labels[code],
            key="page_choice", label_visibility="collapsed",
        )
        if page != st.session_state.page:
            st.session_state.page = page
            st.rerun()

        st.divider()
        st.markdown(f"#### 📊 {t['data_status']}")
        st.markdown(stats_html(index, lang), unsafe_allow_html=True)

        auto = st.toggle(t["auto_refresh"], value=True, key="auto_refresh")
        if st.button(f"🔄 {t['reload_now']}", width="stretch"):
            load_bundle.clear()
            st.session_state["_flash"] = t["reloaded"]
            st.rerun()
        if st.button(f"🧹 {t['reset_chat']}", width="stretch"):
            st.session_state.messages = []
            st.session_state.pop("_flash", None)
            st.rerun()

        st.divider()
        # 「怎么加资料/图片」「C 语言内核」两块属于开发说明，默认收进后台不显示；
        # 需要时用环境变量 RED_AGENT_DEV=1 启动即可重新出现在侧边栏。
        if DEV_PANELS:
            with st.expander(f"📚 {t['howto']}", expanded=False):
                st.markdown(t["howto_body"])

            with st.expander(f"🧩 {t['c_core']}", expanded=False):
                st.caption(t["c_core_info"])
                lib = index.get("lib")
                if lib is not None:
                    engine = getattr(lib, "engine", "c")
                    engine_label = t["engine_c"] if engine == "c" else t["engine_py"]
                    if lang == "en":
                        text = (f"engine: {engine_label}\n"
                                f"graph copy: _runtime/graph_{lib.signature}.dll\n"
                                f"data signature: {lib.signature}")
                    else:
                        text = (f"内核引擎：{engine_label}\n"
                                f"graph.dll 副本：_runtime/graph_{lib.signature}.dll\n"
                                f"数据签名：{lib.signature}")
                    st.code(text, language="text")

        sep = ": " if lang == "en" else "："
        st.caption(f"{t['updated']}{sep}{timestamp_text(index['mtime'])}")
    return auto


# ============================================================
# 4.5 内容数据（时间轴 / 研学路线 / 题库）
# ============================================================
def _load_json(rel: str, default):
    """rel 形如 content/routes.json；找不到就去 content__routes.json。"""
    folder, _, name = rel.partition("/")
    path = fp.resolve(ROOT, folder, name) if name else os.path.join(ROOT, rel)
    if not path:
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def pick_text(obj: dict, key: str, lang: str) -> str:
    """按语言取字段：key_en 优先，没有就回退 key。"""
    if lang == "en":
        value = obj.get(key + "_en")
        if value:
            return value
    return obj.get(key, "") or ""


def load_timeline(lang: str) -> list[dict]:
    items = _load_json("content/timeline.json", []) or []
    return [{"year": it.get("year", ""),
             "label": pick_text(it, "label", lang),
             "text": pick_text(it, "text", lang),
             "entity": it.get("entity", "")} for it in items]


def load_routes(lang: str, index: dict) -> list[dict]:
    """把 routes.json 本地化，并把点位补上实体图片与资料。"""
    data = _load_json("content/routes.json", {}) or {}
    pois = data.get("pois") or {}
    out = []
    for route in data.get("routes") or []:
        ordered = []
        for pid in route.get("pois", []):
            poi = pois.get(pid)
            if not poi:
                continue
            node = index["nodes"].get(poi.get("entity", ""), {})
            image = poi.get("image") or node.get("image") or (poi.get("entity", "") + ".jpg")
            ordered.append({
                "id": pid,
                "entity": poi.get("entity", ""),
                "name": pick_text(poi, "name", lang),
                "addr": pick_text(poi, "addr", lang),
                "intro": pick_text(poi, "intro", lang),
                "lat": poi.get("lat"), "lng": poi.get("lng"),
                "campus": poi.get("campus", ""), "x": poi.get("x"), "y": poi.get("y"),
                "image": image,
                "themes": [str(x).upper() for x in (poi.get("themes") or [])],
                "primary": str(poi.get("primary") or "").upper(),
                "has_image": os.path.exists(os.path.join(ASSETS, image)),
            })
        out.append({
            "id": route.get("id", ""),
            "campus": route.get("campus", "chengnan"),
            "title": pick_text(route, "title", lang),
            "duration": pick_text(route, "duration", lang),
            "summary": pick_text(route, "summary", lang),
            "tags": (route.get("tags_en") if lang == "en" and route.get("tags_en")
                     else route.get("tags", [])),
            "tasks": (route.get("tasks_en") if lang == "en" and route.get("tasks_en")
                      else route.get("tasks", [])),
            "pois": ordered,
        })
    return out


def load_quiz(lang: str) -> list[dict]:
    data = _load_json("content/quiz.json", []) or []
    out = []
    for q in data:
        out.append({
            "id": q.get("id", ""),
            "entity": q.get("entity", ""),
            "q": pick_text(q, "q", lang),
            "options": q.get("options_en") if lang == "en" and q.get("options_en")
                       else q.get("options", []),
            "answer": int(q.get("answer", 0)),
            "explain": pick_text(q, "explain", lang),
        })
    return out


# ============================================================
# 4.6 三个页面
# ============================================================
def render_chat_page(index: dict, lang: str, t: dict) -> None:
    for i, msg in enumerate(st.session_state.messages):
        render_message(msg, index, lang, i)

    if not st.session_state.messages:
        st.markdown(f"#### 👋 {t['examples']}")
        st.caption(t["welcome"])
        picks = [display_name(n, lang) for n in index["kg"]["nodes"][:4]]
        cols = st.columns(len(picks))
        for col, name in zip(cols, picks):
            with col:
                if st.button(name, key=f"ex-{name}", width="stretch"):
                    st.session_state["_pending"] = name
                    st.rerun()

    st.caption(t["footer"])

    # ---- 两点路径工具（C 语言 BFS） ----
    with st.expander(f"🧭 {t['path_tool']}", expanded=False):
        ids = list(index["nodes"])
        c1, c2, c3 = st.columns([3, 3, 2])
        a_id = c1.selectbox(
            t["path_from"], ids, key="path_from",
            format_func=lambda i: display_name(index["nodes"][i], lang),
        )
        b_id = c2.selectbox(
            t["path_to"], ids, key="path_to", index=min(1, len(ids) - 1),
            format_func=lambda i: display_name(index["nodes"][i], lang),
        )
        if c3.button(t["path_btn"], width="stretch"):
            st.session_state.messages.append({
                "role": "user",
                "content": f"{display_name(index['nodes'][a_id], lang)} ↔ "
                           f"{display_name(index['nodes'][b_id], lang)}",
            })
            st.session_state.messages.append(make_path_message(a_id, b_id, index))
            st.rerun()
        st.caption(t["path_caption"])

    # ---- 智能体调用记录（模型 / 参数校验 / 工具 / 耗时）----
    render_agent_log(lang)

    prompt = st.chat_input(t["placeholder"])
    if not prompt:
        prompt = st.session_state.pop("_pending", None)
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append(answer(prompt, index, lang))
        st.rerun()


def goto_page(name: str) -> None:
    """程序化切换页面：必须清掉 radio 的控件状态，否则它会覆盖回去。"""
    st.session_state.page = name
    st.session_state.pop("page_choice", None)
    st.rerun()


def render_graph_page(index: dict, lang: str, t: dict) -> None:
    L = (lambda zh, en: zh) if lang == "zh" else (lambda zh, en: en)
    st.markdown(
        f'<div class="page-head"><div class="eyebrow">KNOWLEDGE GRAPH · 2026</div>'
        f'<h2>🕸️ {t["page_graph"]}</h2><p>{t["graph_hint"]}</p></div>',
        unsafe_allow_html=True,
    )

    nodes_payload = [
        {"id": nid, "label": display_name(node, lang),
         "type": (node.get("type") or "CONCEPT").upper(),
         "typeLabel": type_label(node.get("type"), lang),
         "desc": (node.get("desc_en") if lang == "en" and node.get("desc_en") else node.get("desc", "")),
         "img": thumb_uri(node)}
        for nid, node in index["nodes"].items()
    ]
    edges_payload = [
        {"s": e["from"], "t": e["to"], "rel": rel_label(e["relation"], lang)}
        for e in index["kg"]["edges"]
        if e["from"] in index["nodes"] and e["to"] in index["nodes"]
    ]
    legend = {k: (v[0] if lang == "zh" else v[1]) for k, v in TYPE_LABELS.items()}
    components.html(
        ui_graph.graph_component(
            nodes_payload, edges_payload, legend,
            hint=L("点击节点查看详情 · 滚轮缩放 · 拖拽平移 · 图例可筛选类型",
                   "Click a node for details · scroll to zoom · drag to pan · click the legend to filter"),
            height=720, lang=lang, theme=current_theme(),
        ),
        height=730, scrolling=False,
    )

    ids = list(index["nodes"])
    c1, c2 = st.columns([4, 1])
    picked = c1.selectbox(
        t["view_entity"], ids, key="graph_pick",
        format_func=lambda i: display_name(index["nodes"][i], lang),
    )
    if c2.button(t["view_btn"], width="stretch"):
        st.session_state.messages.append(
            {"role": "user", "content": display_name(index["nodes"][picked], lang)})
        st.session_state.messages.append(
            {"role": "assistant", "kind": "entity", "entity_id": picked})
        goto_page("chat")

    # ---- 实拍影像：把「照片 → 数据」这件事直接摊开给用户看 ----
    shots = [
        ("school", "第一师范主楼", "Main building"),
        ("statue", "毛泽东铜像广场", "Statue square"),
        ("paifang", "城南书院石坊", "Academy archway"),
        ("class8", "第八班教室", "Class Eight classroom"),
        ("dorm8", "第八班寝室", "Class Eight dormitory"),
        ("hall", "大礼堂内景", "Assembly hall"),
        ("courtyard", "校园中庭铜像群", "Courtyard sculptures"),
        ("well", "水井", "The well"),
        ("readingroom", "阅报室", "Reading room"),
        ("playground", "体育锻炼场", "Exercise ground"),
        ("nightclass", "工人夜学", "Night school"),
        ("houzishi", "猴子石缴枪展陈", "Houzishi diorama"),
    ]
    with st.expander(L("📷 城南校区实拍影像（12 张，已用于实体配图）",
                       "📷 Field photos from the Chengnan campus (12, used as entity images)"),
                     expanded=False):
        cols = st.columns(4)
        for i, (eid, zh, en) in enumerate(shots):
            node = index["nodes"].get(eid)
            path = resolve_image(node) if node else None
            with cols[i % 4]:
                if path:
                    st.image(path, width="stretch")
                    st.caption(zh if lang == "zh" else en)
                else:
                    st.caption(L("暂无图片", "No image") + f" · {eid}")

    st.markdown(f"#### 🕰️ {t['timeline_title']}")
    items = load_timeline(lang)
    if items:
        st.markdown(themed_html(ui_graph.timeline_html(items)), unsafe_allow_html=True)


def _all_pois(lang: str, index: dict) -> list[dict]:
    """把三条路线里的点位去重合并（地图/定制路线共用）。"""
    seen, out = set(), []
    for route in load_routes(lang, index):
        for poi in route["pois"]:
            if poi["id"] not in seen:
                seen.add(poi["id"])
                out.append(poi)
    return out


def _card_uri(poi: dict) -> str:
    """路线卡片背景：优先用 360px 缩略图，减小 HTML 体积。"""
    path = os.path.join(ASSETS, poi.get("image", ""))
    if not poi.get("has_image") or not os.path.exists(path):
        return ""
    stem = os.path.splitext(os.path.basename(path))[0]
    thumb = os.path.join(ASSETS, "_thumbs", stem + ".jpg")
    use = thumb if os.path.exists(thumb) else path
    try:
        return "data:image/jpeg;base64," + _b64_file(use, os.path.getmtime(use))
    except OSError:
        return ""


def _route_card_html(route: dict, index: dict, active: bool, lang: str) -> str:
    cover = ""
    if route["pois"]:
        cover = _card_uri(route["pois"][0])
    style = f' style="background-image:url({cover})"' if cover else ""
    tags = "".join(f"<span>{x}</span>" for x in route.get("tags", [])[:3])
    stops = f'{len(route["pois"])} 站' if lang == "zh" else f'{len(route["pois"])} stops'
    return (
        f'<div class="route-card{" active" if active else ""}">'
        f'<div class="rc-bg"{style}></div><div class="rc-shade"></div>'
        f'<div class="rc-body">'
        f'<div class="rc-kicker">{route["duration"]}</div>'
        f'<div class="rc-title">{route["title"]}</div>'
        f'<div class="rc-sub">{route["summary"]}</div>'
        f'<div class="rc-stats"><span>{stops}</span>{tags}</div>'
        f'</div></div>'
    )


def _brief_html(title: str, summary: str, duration: str, tags: list[str],
                n_stops: int, lang: str, extra: str = "") -> str:
    tag_html = "".join(f'<span class="rc-tag">{x}</span>' for x in tags)
    stops = f"{n_stops} 站" if lang == "zh" else f"{n_stops} stops"
    return (
        f'<div class="route-brief"><b>{title}</b>'
        f'<span class="muted">{duration} · {stops}</span>{tag_html}'
        f'<span class="muted" style="flex-basis:100%">{summary}</span>{extra}</div>'
    )


def _stops_html(items: list[dict], lang: str, with_why: bool = True) -> str:
    rows = []
    for n, it in enumerate(items, 1):
        poi = it["poi"]
        bits = [poi["addr"]]
        if n > 1 and it.get("dist") is not None:
            bits.append(("距上一站 %d 跳" if lang == "zh" else "%d hop(s) from previous") % it["dist"])
        if it.get("match"):
            bits.append("主题匹配" if lang == "zh" else "theme match")
        why = poi["intro"] if with_why else ""
        rows.append(
            f'<div class="stop-row"><div class="stop-no">{n}</div><div class="stop-body">'
            f'<div class="stop-name">{poi["name"]}</div>'
            f'<div class="stop-meta">{" · ".join(bits)}</div>'
            f'<div class="stop-why">{why}</div></div></div>'
        )
    return '<div class="stop-list">' + "".join(rows) + "</div>"


def _poi_cards(pois: list[dict], index: dict, lang: str, t: dict,
               key_prefix: str, items: list[dict] | None = None) -> None:
    by_id = {it["poi"]["id"]: it for it in (items or [])}
    for start in range(0, len(pois), 3):
        cols = st.columns(3)
        for col, poi in zip(cols, pois[start:start + 3]):
            it = by_id.get(poi["id"], {})
            badge = ""
            if it.get("match"):
                badge = ('<span class="sv-where">主题匹配</span>' if lang == "zh"
                         else '<span class="sv-where">theme match</span>')
            cover = _card_uri(poi)
            style = f' style="background-image:url({cover})"' if cover else ""
            with col:
                st.markdown(
                    f'<div class="poi-grid-card"><div class="pc-img"{style}></div>'
                    f'<div class="pc-body"><div class="pc-title">{poi["name"]} {badge}</div>'
                    f'<div class="pc-addr">{poi["addr"]}</div>'
                    f'<div class="pc-intro">{poi["intro"]}</div></div></div>',
                    unsafe_allow_html=True,
                )
                if st.button(t["open_entity"], key=f"{key_prefix}-ent-{poi['id']}",
                             width="stretch"):
                    st.session_state.messages.append({"role": "user", "content": poi["name"]})
                    st.session_state.messages.append(
                        {"role": "assistant", "kind": "entity", "entity_id": poi["entity"]})
                    goto_page("chat")


def _tasks_panel(tasks: list[str], key: str, lang: str, t: dict) -> list[bool]:
    title = "✅ 研学任务卡" if lang == "zh" else "✅ Field tasks"
    with st.expander(title, expanded=True):
        flags = [st.checkbox(task, key=f"{key}-task-{j}") for j, task in enumerate(tasks)]
        done = sum(1 for f in flags if f)
        pct = int(round(done / max(len(tasks), 1) * 100))
        st.markdown(
            f'<div class="progress-wrap"><div class="plabel"><span>任务进度</span>'
            f'<span>{done} / {len(tasks)}</span></div>'
            f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%"></div></div></div>',
            unsafe_allow_html=True,
        )
    return flags


def _export_panel(route: dict, pois: list[dict], index: dict, lang: str, t: dict,
                  flags: list[bool], quiz_rows: list[dict], key: str) -> None:
    if st.button(f"📄 {t['export']}", key=f"{key}-export", width="stretch"):
        data, fname, mime = report_mod.build_report(
            route, pois, index["nodes"], lang, flags, quiz_rows)
        st.session_state[f"{key}-report"] = (data, fname, mime)
    stored = st.session_state.get(f"{key}-report")
    if stored:
        st.success(t["export_ready"])
        st.download_button(t["download"], data=stored[0], file_name=stored[1],
                           mime=stored[2], key=f"{key}-download", width="stretch")


def _quiz_panel(route: dict, index: dict, lang: str, t: dict) -> list[dict]:
    st.markdown(f"#### 📝 {t['quiz']}")
    quiz = load_quiz(lang)
    if not quiz:
        st.info("content/quiz.json 缺失")
        return []
    quiz_key = f"quiz-{route['id']}-{lang}"
    picked_ids = st.session_state.get(quiz_key)
    if not picked_ids:
        picked_ids = [q["id"] for q in random.sample(quiz, min(5, len(quiz)))]
        st.session_state[quiz_key] = picked_ids
    by_id = {q["id"]: q for q in quiz}
    selected = [by_id[i] for i in picked_ids if i in by_id]

    if st.button(t["quiz_new"], key=f"newquiz-{route['id']}"):
        st.session_state[quiz_key] = [q["id"] for q in random.sample(quiz, min(5, len(quiz)))]
        st.session_state.pop(f"quizres-{route['id']}", None)
        st.rerun()

    answers = []
    for n, q in enumerate(selected, 1):
        answers.append(st.radio(
            f"{n}. {q['q']}", options=list(range(len(q["options"]))),
            index=None, key=f"ans-{route['id']}-{q['id']}",
            format_func=lambda k, opts=q["options"]: opts[k],
        ))

    if st.button(t["quiz_submit"], key=f"submit-{route['id']}", width="stretch"):
        if any(a is None for a in answers):
            st.warning(t["quiz_need_all"])
        else:
            rows = []
            for q, a in zip(selected, answers):
                rows.append({
                    "q": q["q"], "chosen": q["options"][a],
                    "answer": q["options"][q["answer"]],
                    "ok": a == q["answer"], "explain": q["explain"],
                    "entity": q["entity"],
                })
            st.session_state[f"quizres-{route['id']}"] = rows

    result = st.session_state.get(f"quizres-{route['id']}")
    if result:
        score = sum(1 for r in result if r["ok"])
        pct = int(score / max(len(result), 1) * 100)
        st.markdown(
            f'<div class="progress-wrap"><div class="plabel">'
            f'<span>{t["quiz_score"]}</span><span>{score} / {len(result)}</span></div>'
            f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%"></div></div></div>',
            unsafe_allow_html=True,
        )
        if score == len(result):
            st.success(t["quiz_all_right"])
        for n, row in enumerate(result, 1):
            mark = "✅" if row["ok"] else "❌"
            st.markdown(f"{mark} **{n}. {row['q']}**")
            st.caption(f"{t['quiz_score']}：{row['chosen']} ｜ {t['correct']}：{row['answer']}")
            if row["explain"]:
                st.caption(row["explain"])
    return result or []


def _route_detail(route: dict, pois: list[dict], index: dict, lang: str, t: dict,
                  key: str, items: list[dict] | None = None) -> None:
    tags = route.get("tags", [])
    st.markdown(_brief_html(route["title"], route["summary"], route["duration"],
                            tags, len(pois), lang), unsafe_allow_html=True)

    c_map, c_list = st.columns([1.45, 1])
    with c_map:
        map_pois = [p for p in pois if p.get("x") is not None and p.get("y") is not None]
        if map_pois:
            campus = route.get("campus") or map_pois[0].get("campus") or "chengnan"
            map_name = "城南校区 · 手绘导览图" if campus == "chengnan" else "东方红校区 · 手绘导览图"
            if lang == "en":
                map_name = "Chengnan Campus · illustrated map" if campus == "chengnan" \
                    else "Dongfanghong Campus · illustrated map"
            payload = [dict(p, img=_card_uri(p)) for p in map_pois]
            components.html(
                ui_campus_map.map_component(
                    payload, map_uri("chengnan_route" if campus == "chengnan" else "dongfanghong_route"),
                    map_name, height=500, route_title=route["title"],
                    note=t["map_note"], lang=lang, theme=current_theme(),
                ),
                height=560, scrolling=False,
            )
        else:
            components.html(
                themed_html(ui_map.map_component(pois, lang, height=440,
                                                 route_title=route["title"],
                                                 offline_note=t["map_note"])),
                height=500, scrolling=False,
            )
    with c_list:
        st.markdown(f"**{'行程时间轴' if lang == 'zh' else 'Itinerary'}**")
        st.markdown(_stops_html(items or [{"poi": p} for p in pois], lang),
                    unsafe_allow_html=True)

    st.markdown(f"#### 📍 {t['poi_list']}")
    _poi_cards(pois, index, lang, t, key, items)

    flags = _tasks_panel(route.get("tasks", []), key, lang, t)
    quiz_rows = _quiz_panel(route, index, lang, t)
    st.divider()
    _export_panel(route, pois, index, lang, t, flags, quiz_rows, key)


def _render_preset_routes(index: dict, lang: str, t: dict) -> None:
    routes = load_routes(lang, index)
    if not routes:
        st.info("content/routes.json 缺失 / missing")
        return
    st.markdown(f"#### 🗺️ {t['choose_route']}")
    current = st.session_state.get("study_route_id")
    if current not in {r["id"] for r in routes}:
        current = routes[0]["id"]
        st.session_state["study_route_id"] = current

    for start in range(0, len(routes), 3):
        cols = st.columns(3)
        for col, route in zip(cols, routes[start:start + 3]):
            with col:
                st.markdown(_route_card_html(route, index, route["id"] == current, lang),
                            unsafe_allow_html=True)
                label = ("已选择" if route["id"] == current else "进入路线") if lang == "zh" \
                    else ("Selected" if route["id"] == current else "Open route")
                if st.button(label, key=f"pick-{route['id']}", width="stretch",
                             disabled=route["id"] == current):
                    st.session_state["study_route_id"] = route["id"]
                    st.rerun()

    route = next(r for r in routes if r["id"] == current)
    _route_detail(route, route["pois"], index, lang, t, f"preset-{route['id']}")


def _render_custom_route(index: dict, lang: str, t: dict) -> None:
    st.markdown(f"#### ✨ {t['custom_route']}")
    st.caption(t["custom_hint"])
    all_pois = _all_pois(lang, index)
    if not all_pois:
        st.info("content/routes.json 缺失")
        return

    campus_labels = {"chengnan": "🏛️ 城南校区", "dongfanghong": "🌳 东方红校区"}
    campus = st.radio(
        "校区" if lang == "zh" else "Campus", list(campus_labels), horizontal=True,
        format_func=lambda c: campus_labels[c], key="cr_campus",
        label_visibility="collapsed",
    )
    pois = [p for p in all_pois if p.get("campus") == campus]
    if not pois:
        st.info("这个校区还没有可排的点位。")
        return

    kinds = [("PERSON", "👤 " + t["interest_person"]),
             ("PLACE", "🏛️ " + t["interest_place"]),
             ("EVENT", "📌 " + t["interest_event"]),
             ("CONCEPT", "💡 " + t["interest_concept"])]
    kind_labels = dict(kinds)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="step-card"><div class="step-no">STEP 01</div>'
            f'<h4>{t["interest"]}</h4><p>选一个你最想追的主题，点位会按 themes 标签匹配。</p></div>',
            unsafe_allow_html=True)
        kind = st.radio(t["interest"], [k for k, _ in kinds], horizontal=True,
                        format_func=lambda k: kind_labels[k], key="cr_kind",
                        label_visibility="collapsed")
    with c2:
        st.markdown(
            f'<div class="step-card"><div class="step-no">STEP 02</div>'
            f'<h4>{t["hours"]}</h4><p>2 小时 3 站，3 小时 4 站，4 小时 6 站。</p></div>',
            unsafe_allow_html=True)
        hours = st.radio(t["hours"], [2, 3, 4], index=1, horizontal=True,
                         format_func=lambda h: f"{h} {t['hours_unit']}", key="cr_hours",
                         label_visibility="collapsed")
    with c3:
        st.markdown(
            f'<div class="step-card"><div class="step-no">STEP 03</div>'
            f'<h4>{t["start_from"]}</h4><p>从你所在的位置出发，减少折返。</p></div>',
            unsafe_allow_html=True)
        start = st.selectbox(
            t["start_from"], [p["entity"] for p in pois], key=f"cr_start_{campus}",
            format_func=lambda e: display_name(index["nodes"].get(e, {"name": e, "id": e}), lang),
            label_visibility="collapsed",
        )

    if st.button(f"✨ {t['generate']}", key="cr_generate", width="stretch"):
        st.session_state["cr_result"] = custom_route.generate(index, pois, kind, hours, start)
        st.session_state["cr_result"]["campus"] = campus
        st.session_state["cr_params"] = (campus, kind, hours, start)

    result = st.session_state.get("cr_result")
    if not result:
        st.markdown(
            '<div class="plan-hint">选好主题、时长和起点后，点上面的按钮生成路线；'
            '系统会给出地图、时间轴、逐站讲解、任务卡和 docx 小结。</div>',
            unsafe_allow_html=True,
        )
        st.markdown("#### 算法怎么排")
        a1, a2, a3 = st.columns(3)
        with a1:
            st.markdown(
                '<div class="step-card"><div class="step-no">MATCH</div><h4>① 主题匹配</h4>'
                '<p>点位的 themes 标签与兴趣主题一致时加 1.5 分；'
                '例如「人物」主题优先选与毛泽东关系密集的点位。</p></div>',
                unsafe_allow_html=True)
        with a2:
            st.markdown(
                '<div class="step-card"><div class="step-no">DISTANCE</div><h4>② BFS 距离</h4>'
                '<p>用 C 内核的 find_path 算「上一站 → 候选点」的最短跳数，'
                '跳数越少分越高，避免在校园里来回折返。</p></div>',
                unsafe_allow_html=True)
        with a3:
            st.markdown(
                '<div class="step-card"><div class="step-no">ORDER</div><h4>③ 贪心排序</h4>'
                '<p>从起点开始每次挑「主题更契合、跳数更小」的下一点，'
                '2 / 3 / 4 小时分别截取 3 / 4 / 6 站。</p></div>',
                unsafe_allow_html=True)
        st.markdown(f"#### 可用的 {len(pois)} 个点位")
        icons = {"PLACE": "🏛️", "EVENT": "📌", "PERSON": "👤", "CONCEPT": "💡"}
        chips = "".join(
            f'<span class="poi-chip">{icons.get((p.get("themes") or ["PLACE"])[0], "📍")} '
            f'{p["name"]}</span>' for p in pois)
        st.markdown(f'<div class="poi-chips">{chips}</div>', unsafe_allow_html=True)
        return
    if st.session_state.get("cr_params") != (campus, kind, hours, start):
        st.warning("参数已修改，请重新生成路线。" if lang == "zh"
                   else "Parameters changed — generate again.")
        return

    items = result["items"]
    kind_name = kind_labels.get(result["kind"], result["kind"])
    campus_name = campus_labels.get(campus, campus)
    if lang == "zh":
        summary = (f"按「{kind_name}」主题排的 {result['hours']} 小时路线："
                   f"主题匹配的点位优先，再按知识图谱跳数就近排序，减少折返。")
    else:
        summary = (f"A {result['hours']}-hour route for the “{kind_name}” theme: "
                   f"theme-matched stops first, then ordered by graph hop distance to reduce backtracking.")
    route = {
        "id": "custom", "title": t["custom_route"], "summary": summary,
        "duration": f"{result['hours']} {t['hours_unit']}",
        "tags": [campus_name, kind_name],
        "tasks": custom_route.make_tasks(items, lang),
        "campus": result.get("campus", campus),
    }
    _route_detail(route, [it["poi"] for it in items], index, lang, t,
                  f"custom-{result['hours']}-{result['kind']}", items)


def render_study_page(index: dict, lang: str, t: dict) -> None:
    n_nodes = len(index["nodes"])
    n_edges = len(index["kg"]["edges"])
    n_routes = len(load_routes(lang, index))
    n_pois = len(_all_pois(lang, index))
    if lang == "zh":
        lead = (f"把 {n_nodes} 个实体、{n_edges} 条关系变成一条走得通的路线："
                f"先选主题，再按时长裁站，最后导出研学小结。")
        meta = [f"{n_routes} 条主题路线", f"{n_pois} 个点位", "2 / 3 / 4 小时", "docx 导出"]
    else:
        lead = (f"Turn {n_nodes} entities and {n_edges} relations into a walkable route: "
                f"pick a theme, fit the duration, export a report.")
        meta = [f"{n_routes} route themes", f"{n_pois} stops", "2 / 3 / 4 hours", "docx export"]
    st.markdown(
        f'<div class="study-hero"><div class="eyebrow">STUDY ROUTE STUDIO</div>'
        f'<h2>🎒 {t["page_study"]}</h2><p>{lead}</p>'
        f'<div class="hero-meta">' + "".join(f"<span>{m}</span>" for m in meta) +
        '</div></div>',
        unsafe_allow_html=True,
    )

    mode = st.radio(
        "mode", ["preset", "custom"], horizontal=True,
        format_func=lambda m: ("🗺️ 经典路线" if m == "preset" else "✨ AI 定制") if lang == "zh"
        else ("🗺️ Curated routes" if m == "preset" else "✨ AI planner"),
        key="study_mode", label_visibility="collapsed",
    )
    if mode == "custom":
        _render_custom_route(index, lang, t)
    else:
        _render_preset_routes(index, lang, t)


# ============================================================
# 5. 主流程
# ============================================================
# 主题要先于样式注入确定下来，否则注入的还是上一次的主题
# 默认亮色：第一次打开就是 ☀️ 亮色模式（想要深色在侧边栏「主题」里切换）
if "theme" not in st.session_state:
    st.session_state.theme = THEME_LIGHT

inject_css()

if "lang" not in st.session_state:
    st.session_state.lang = "zh"
if "page" not in st.session_state:
    st.session_state.page = "chat"
if "messages" not in st.session_state:
    st.session_state.messages = []

signature = data_signature()

try:
    index = load_bundle(signature)
except Exception as exc:  # C 内核或数据有问题时给可读的提示，而不是整页崩掉
    st.error("数据加载失败 / Failed to load data\n\n```\n" + str(exc) + "\n```")
    st.stop()

lang = st.session_state.lang
t = TEXT[lang]


@st.fragment(run_every="3s")
def auto_watch(sig: str) -> None:
    """每 3 秒嗅一次文件指纹，数据变了就整页刷新。"""
    if data_signature() != sig:
        st.rerun()


auto_refresh = sidebar(index, lang)
if auto_refresh:
    auto_watch(signature)

# ---- 顶部主视觉 ----
# 标题右侧的小图标：点一下打开湖南第一师范学院官网
HNFS_URL = "https://www.hnfnu.edu.cn/"
HNFS_LINK = (
    f'<a class="h1-link" href="{HNFS_URL}" target="_blank" rel="noopener noreferrer" '
    f'aria-label="湖南第一师范学院官网" title="湖南第一师范学院官网 · hnfnu.edu.cn">'
    '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<path d="M10.6 13.4a4 4 0 0 0 5.7 0l2.5-2.5a4 4 0 0 0-5.7-5.7l-1.5 1.5" '
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
    '<path d="M13.4 10.6a4 4 0 0 0-5.7 0l-2.5 2.5a4 4 0 0 0 5.7 5.7l1.5-1.5" '
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
    '</svg></a>'
)
if lang == "zh":
    _title_html = (f'🚩 {t["app_title"]} '
                   f'<span class="h1-en">RedTrace AI {HNFS_LINK}</span>')
else:
    _title_html = f'🚩 {t["app_title"]} {HNFS_LINK}'
_tag_chips = "".join(
    f'<span class="hero-tag">{chip.strip()}</span>'
    for chip in t["tags"].split("·")
)
st.markdown(
    f'<div class="hero">'
    f'<span class="badge">{t["badge"]}</span>'
    f'<h1>{_title_html}</h1>'
    f'<p>{t["subtitle"]}</p>'
    f'<div class="hero-tags">{_tag_chips}</div>'
    f'</div>',
    unsafe_allow_html=True,
)
st.markdown(stats_html(index, lang), unsafe_allow_html=True)

if st.session_state.get("_flash"):
    st.success(st.session_state.pop("_flash"))
if st.session_state.get("_sig") and st.session_state["_sig"] != signature:
    st.toast(t["data_changed"])
st.session_state["_sig"] = signature

# ---- 按页面渲染 ----
if st.session_state.page == "graph":
    render_graph_page(index, lang, t)
elif st.session_state.page == "study":
    render_study_page(index, lang, t)
else:
    render_chat_page(index, lang, t)

