# 红脉智谱 RedTrace AI —— 使用说明

> **主标题**：红脉智谱（RedTrace AI）
> **副标题**：一师红色文化知识图谱与智能研学平台
> **功能标签**：关系挖掘 · 人物追踪 · AI 定制路线

一个「知识图谱 + C 语言邻接表」的红色文化研学平台。
所有内容都放在项目目录的文件里，**改文件 → 保存 → 页面 3 秒内自动更新**，不用重启、不用重新编译。

---

## 1. 怎么运行

```bat
cd /d <本目录>
.venv\Scripts\python.exe -m streamlit run app.py
```

或者直接双击 **`启动红脉智谱.bat`**（会自动找可用的 Python 环境）。浏览器会自动打开 <http://localhost:8501>。
停止：在命令行里按 `Ctrl + C`。

依赖：`streamlit`（1.66）与 `python-docx`（导出 docx 用）。
换机器部署：双击 **`安装运行环境.bat`**，或 `.venv\Scripts\python.exe -m pip install -r requirements.txt`。

> 侧边栏默认只保留**语言、页面导航、数据状态、自动刷新、重新加载、清空对话、最后更新时间**。
> 原来那两块开发说明（「怎么加资料 / 图片」「C 语言内核」）已经收进后台，不再占界面；
> 需要时用环境变量把它调出来：
>
> ```bat
> set RED_AGENT_DEV=1
> .venv\Scripts\python.exe -m streamlit run app.py
> ```

### 1.1 局域网部署（断网也能让别人用）

默认 `启动红脉智谱.bat` 只监听本机。要让同一 Wi-Fi 下的手机/电脑访问：

1. 双击 **`部署\启动局域网服务.bat`** —— 它用 `--server.address 0.0.0.0 --server.port 8501` 启动，
   并先跑 `部署\lan_info.py`：自动识别本机 IP、生成 `部署\访问二维码.png` 和 `部署\访问入口.html`（离线可开）；
2. 其他人连**同一 Wi-Fi**，扫二维码或输入 `http://<本机IP>:8501`；
3. 打不开：Windows 防火墙允许访问，或右键 `部署\允许防火墙放行.bat` 以管理员运行；
   校园网可能开了 AP 隔离，可改用手机热点。

**离线可用性**：页面全部资源都在本机（背景图 base64 内联、Leaflet 本地、力导图自写、二维码本地生成），
唯一需要外网的是地图**底图瓦片**——断网时会自动降级成「深色底 + 地标 + 路线虚线」，功能不受影响。
想要真正公网可访问（域名/异地访问）必须有一台公网服务器或内网穿透，那必然需要联网。

---

## 2. 项目做了什么

| 项目 | 说明 |
| --- | --- |
| 品牌 | 主标题 **红脉智谱（RedTrace AI）**、副标题「一师红色文化知识图谱与智能研学平台」、功能标签「关系挖掘 · 人物追踪 · AI 定制路线」，都在 `app.py` 的 `TEXT` 里改 |
| 语言选择 | 下拉里的 **中文** / **English**，整页文案（含侧边栏、按钮、分区标题）都会跟着切换 |
| 视觉 | 深红主题 + 背景图 + 毛玻璃卡片；主标题改成渐变主视觉区；聊天气泡、按钮、输入框统一圆角 |
| 背景图 | `assets/bg.jpg`（可替换成自己的照片，会自动加暗色遮罩保证文字可读） |
| 内容 | 实体卡片里显示：类型标签、`materials/` 里的详细资料、配图、直接关联、**反向关联**、两跳间接关联、资料来源、C 层原始返回 |
| 交互 | 关联实体是可点的按钮，点一下就能顺着关系继续追问；未命中时给出相近实体建议 |
| 数据 | 支持 `aliases` 别名、`desc` 简介；数据变化自动热加载（见第 4 节） |
| 侧边栏 | 只保留必要项：语言、页面导航、数据状态、自动刷新、重新加载、清空对话、最后更新时间（时间显示为 `2026-10-24 13:24`）。开发说明面板默认隐藏，见第 1 节 |
| 三个页面 | 侧边栏切换 **问答 / 知识图谱 / 研学**：问答查实体与路径，图谱看网络结构与时间轴，研学走路线、做任务、随堂测评并导出小结 |
| 两点路径 | `graph.c` 里新增 **BFS 最短路径** `find_path()`：先只走正向边（显示「A —关系→ B」），找不到再允许走反向边（显示「← 关系」），页面上直接给出跳数与 C 层耗时 |
| 图谱可视化 | 自写的 canvas 力导向图（无第三方库、离线可用）：按类型着色、可拖动、点节点高亮一跳邻居并列出关系 |
| 时间轴 | `content/timeline.json`：1913–1921 年大事，中英双语 |
| 预置研学 | `content/routes.json` 三条路线（半天 / 一日 / 精神传承），Leaflet 地图上按 1-2-3 顺序打点，**点地标弹出地址、照片、简介**；配任务卡、随堂测评（`content/quiz.json`）与 `docx` 小结导出 |
| **AI 定制路线** | 研学页顶部：选兴趣主题（人物/旧址/事件/精神理念）+ 时长（2/3/4 小时）+ 起点 → `custom_route.py` 按「实体类型匹配 + C 语言 BFS 跳数就近排序」生成路线，自动附带地图、点位讲解与 3 条任务卡，可单独导出 docx |

### 2.1 AI 定制路线怎么算的

1. **主题匹配**：点位对应实体类型 == 所选兴趣（人物 / 旧址 / 事件 / 精神理念）时加最高分；
2. **距离**：用 `graph.dll` 的 `find_path` 算「起点 → 该点位」的最短跳数，越近分越高；
3. **排序**：从起点做贪心最近邻（每次挑跳数最小的下一个点），得到一条走得顺的路线；
4. **配套**：按点位数量（2h→3 个、3h→4 个、4h→6 个）截断，生成地图、讲解、任务卡。

> 这是**图谱推荐算法**，不是大模型自由生成：结果可解释、可复现，也不会编出资料里没有的点位。

### 2.2 C 内核对 Python 的性能对比

同一张图、同一批随机实体对（3000 组），C 与 Python 都跑 BFS 取中位数：

| 图规模 | C 调用总耗时 | 其中 ctypes 开销 | C 内核净耗时 | Python BFS |
| --- | --- | --- | --- | --- |
| 33 节点 / 47 边（本项目） | 1.16 µs | 0.19 µs | 0.97 µs | 2.05 µs |
| 200 节点 / 600 边（合成压测） | 3.72 µs | 0.19 µs | 3.53 µs | 14.47 µs |

结论：本项目规模下两者都是微秒级，C 约快 1.8 倍；图放大到 200 节点后 C 快约 3.9 倍，
因为 BFS 在 C 里用连续数组 + 静态队列，Python 侧还要建 set / deque 和回溯列表。
`ctypes` 每调用固定约 0.19 µs，所以这里特意把「调用开销」和「内核净耗时」分开列，避免夸大。
（复测脚本思路见第 6 节 `_bench` 说明；实测环境为 Windows + CPython 3.12。）

### 2.1 本次接入的资料与图片

内容来自 `D:\A3作业\数据库\毛泽东一师求学时期人物与事件整理（含来源）.docx`：

- **33 个实体、46 条关系**（在原图谱基础上，按文档补充了 4 条关系：
  何叔衡—创办—新民学会成立、萧子升—成员—新民学会、杨昌济—影响—新民学会、杨昌济—用作教材—《伦理学原理》批注）。
- `materials/<id>.md` + `materials/<id>.en.md`：每个实体**中英各一页**，内容为「核心身份 + 与一师相关的关键事实 + 知识图谱关联 + 资料来源与要点」，
  其中事实与来源表全部取自该 Word 文档，`kg.json` 的 `sources` 保存原文链接（卡片底部可点）。
- `assets/<id>.jpg`：33 张配图，卡片上显示来源署名（`image_credit` / `image_credit_en` 字段）。

**整页双语**：实体名（`name_en`）、资料正文、关联分组、来源表、图片署名、按钮、提示语都会随「中文 / English」切换，
英文界面里不会混入中文（唯一例外是「查看 C 层原始返回」里 C 直接输出的原始字符串）。

图片来源分三类，均记录在 `kg.json` 的 `image_credit` / `image_source`：

| 来源 | 数量 | 说明 |
| --- | --- | --- |
| Wikimedia Commons | 16 | 历史人物肖像与旧址照片，均为 **Public domain / CC0 / CC BY-SA**，可放心用于作业 |
| 百度图片检索 | 13 | 建筑与展陈（如第八班教室、君子亭、湘江评论创刊号），卡片标注了检索关键词与原页面标题 |
| 程序生成示意图 | 4 | 大礼堂、尊师重道、读无字之书、萧子升暂无可靠实拍图，用统一风格示意图并在图内注明「暂无实拍图片」 |

> 作业提交时建议保留这份说明：Commons 的图片授权信息可在对应文件页面查到；
> 网络检索的图片请按学校要求注明出处（每张图卡片上都带了来源文字）。

---

## 3. 怎么接入你已经整理好的资料

### 3.1 实体和关系：`kg.json`

```json
{
  "nodes": [
    {
      "id": "mao",
      "name": "毛泽东",
      "name_en": "Mao Zedong",
      "type": "PERSON",
      "image": "mao.jpg",
      "image_credit": "图片：Wikimedia Commons《毛泽东 1919 年在长沙》",
      "image_credit_en": "Image: Wikimedia Commons — Mao Zedong in Changsha, 1919",
      "aliases": ["毛主席", "润之", "Mao", "Chairman Mao"],
      "sources": ["http://...", "http://..."],
      "desc": "一师第八班学生，青年时期核心人物。",
      "desc_en": "Student of Class Eight at Hunan First Normal School; the central figure of his youth."
    }
  ],
  "edges": [
    { "from": "yangchangji", "to": "mao", "relation": "TEACHER_OF" }
  ]
}
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 是 | 唯一英文标识，≤31 字节，**不能有空格**，也是资料/图片的文件名 |
| `name` | 是 | 中文显示名称，≤63 字节，不能有空格或制表符 |
| `name_en` | 否 | 英文显示名。**切换成 English 时卡片标题、关联按钮都显示它**；建议补上，并同时放进 `aliases`，这样英文提问也能命中 |
| `type` | 否 | `PERSON` / `PLACE` / `EVENT` / `ORG` / `CONCEPT` / `WORK`，决定类型标签 |
| `image` | 否 | `assets/` 下的文件名；不写就自动找 `assets/<id>.jpg` |
| `image_credit` / `image_credit_en` | 否 | 卡片上图片下方的署名（中／英各一条） |
| `aliases` | 否 | 别名数组，用来提高命中率（如「毛主席」「润之」「Mao」） |
| `sources` | 否 | 资料来源链接数组，显示在卡片底部 |
| `desc` / `desc_en` | 否 | 一句话简介；没有 `materials/<id>.md` 时作为正文兜底 |

`edges` 里的 `relation` 是关系类型，例如 `TEACHER_OF` `FOUNDED` `PARTICIPATED_IN`。
中英文标签在 `app.py` 的 `REL_LABELS` 里，一行两列；没登记的会原样显示英文。

### 3.2 详细资料：`materials/`

在 `materials/` 下按实体 `id` 建 Markdown 文件，正文会直接显示在实体卡片里：

```
materials/mao.md        ← 中文界面用（也作为英文界面的兜底）
materials/mao.zh.md     ← 只给中文界面用（优先级高于 mao.md）
materials/mao.en.md     ← 只给英文界面用
```

查找优先级：`<id>.<当前语言>.md` → `<id>.md` → `kg.json` 的 `desc` / `desc_en` → 「还没有资料」提示。

**当前项目里 33 个实体都有 `mao.md`（中文）和 `mao.en.md`（英文）两份**，切换语言时整页——包括正文、关联分组、来源表、图片署名——都会跟着变。
新增实体想双语，就成对写 `<id>.md` + `<id>.en.md`；只写 `<id>.md` 也能用，但英文界面会显示中文正文。

正文支持 Markdown：标题、列表、`> 引用`、**加粗**、表格、[链接](http://…)。

### 3.3 图片：`assets/`

| 文件 | 作用 |
| --- | --- |
| `assets/<id>.jpg` | 该实体的配图，自动匹配（也支持 `.jpeg` `.png` `.webp`） |
| `assets/bg.jpg` | 页面背景图，换成自己的照片即可（也支持 `bg.png` / `bg.webp`） |
| `assets/mao.jpg` | 现有示例：毛泽东 |

- `kg.json` 里写 `"image": "xxx.jpg"` 也可以，优先于自动匹配。
- 名为 `placeholder.*` 的图会被忽略（表示「暂无图片」，不会显示灰图）。
- 建议图片宽度 600–1000px，单张 < 500 KB，否则首屏会变慢。
- 背景图建议 1600×900 以上、横向构图：页面会自动叠加从深到浅的暗色遮罩，所以照片本身亮一点也没关系。

### 3.4 研学内容：`content/`

| 文件 | 内容 | 怎么改 |
| --- | --- | --- |
| `content/routes.json` | 三条路线与 8 个点位 | `pois` 里给每个点位写 `name/addr/intro/lat/lng/entity`（`entity` 指向 `kg.json` 的实体，图片和资料自动复用）；`routes` 里按顺序列点位 id，并写 `tasks` 任务卡 |
| `content/quiz.json` | 15 道单选题 | 每题写 `q`、`options`、`answer`（正确项下标，从 0 开始）、`explain`、`entity`（错题会回链到实体）；英文版加 `q_en` / `options_en` / `explain_en` |
| `content/timeline.json` | 时间轴 | `year` + `label` + `text` + `entity`，英文加 `label_en` / `text_en` |

点位坐标是**近似值**（页面地图下方有说明），只用于导览示意；同一校区内的点位做了小幅偏移，避免地标重叠。
地图用本地内置的 Leaflet（`static/leaflet.js|css`），瓦片来自 OpenStreetMap：联网时是真实底图，断网时仍能看到地标与路线。

---

## 4. 修改之后，页面怎么自动更新

### 4.1 直接改文件就行

改了 `kg.json`、`materials/*.md`、往 `assets/` 里加了图，**保存后 3 秒内**页面顶部会弹出「检测到数据文件变化，已自动更新」，内容随之刷新。
侧边栏有开关可以关掉自动刷新；也可以点 **🔄 立即重新加载** 手动刷新。

### 4.2 为什么能自动更新（原来的坑）

`graph.c` 里图数据是 C 进程里的静态数组，而 `graph.dll` 一个进程只加载一次。
原来的写法只在启动时 `load_graph()` 一次，所以**改完 `kg.json` 页面永远是旧数据**，必须重启。

现在的做法（见 `c_core.py`）：

1. 每次运行把 `kg.json` 生成 `nodes.txt` / `edges.txt`；
2. 按这两个文件的内容算一个**数据签名**；
3. 按签名把 `graph.dll` 复制成 `_runtime/graph_<签名>.dll` 再加载 —— 文件名不同，Windows 就当成新模块，全局变量从零开始；
4. `load_graph()` 读到的就是最新数据，旧模块留在内存里不影响。

所以改完数据结构**不用重启、不用重装、不用重新编译**。
`nodes.txt` / `edges.txt` 是自动生成的中间文件，不用手改；`_runtime/` 里是自动管理的 DLL 副本，删掉也没关系（下次运行会重建）。

### 4.3 什么时候需要重启

- 改了 `app.py`：保存后 Streamlit 自动重跑（已开 `runOnSave`），一般不用手动重启；
- 改了 `.streamlit/config.toml` 的主题：需要重启一次；
- 改了 `graph.c` 并重新编译：`c_core.py` 会检测到源文件更新并自动重编译（需要本机有 `gcc`），没有编译器时会继续用旧的 `graph.dll`。

---

## 5. 限制与排错

**C 侧上限（`graph.c` 里的静态数组）**：最多 **200 个实体、600 条关系**。
超了页面会直接提示「超过上限」而不是崩溃。要再扩容就改 `graph.c` 顶部的常量后重新编译：

```bat
gcc -std=c99 -O2 -shared -fPIC -o graph.dll graph.c
```

本机没装 gcc 也能跑（直接用仓库里编译好的 `graph.dll`）。想重新编译的两种办法：
1. 装 MinGW-w64 并把 `gcc` 加进 PATH；
2. 把便携版 [w64devkit](https://github.com/skeeto/w64devkit/releases) 解压到项目下的 `tools/` 目录，`c_core.py` 会自动识别 `tools/**/bin/gcc.exe`。

**C 内核接口**（`graph.c` 导出，Python 用 ctypes 调用）：

| 函数 | 作用 |
| --- | --- |
| `graph_api_version()` | 内核版本号（当前 2，带 BFS） |
| `load_graph()` | 读 `nodes.txt` / `edges.txt`，同时建有向表与无向表 |
| `query_neighbors(id, buf, n)` | 一跳邻居（有向），返回条数 |
| `find_path(from, to, buf, n)` | BFS 最短路径（先正向、后无向），返回跳数 |
| `get_node_count()` / `get_edge_count()` | 节点 / 边数 |

**字段长度**：`id` ≤ 31 字节，`name` ≤ 63 字节，`relation` ≤ 31 字节；三者都不能含空格/制表符（C 用 `sscanf("%s")` 解析）。
超长会在页面上给出明确报错，告诉你是哪个字段。

**查不到实体 / 命中错实体**：给该实体加 `aliases`；匹配规则是「最长别名优先」，所以「湖南第一师范旧址」不会被「第一师范旧址」抢走。

**图片不显示**：确认文件名与 `id` 一致、扩展名在支持列表里、放进了 `assets/`；`placeholder.*` 会被忽略。

**看到 `build_and_load() takes 0 positional arguments but 1 was given`**：
Streamlit 只重新执行主脚本，**不会重新 import 已经加载的模块**，所以升级 `c_core.py` 后，
正在运行的服务里可能还是旧版函数（浏览器刷新没用，模块还在内存里）。
新版 `app.py` 改成每次按文件路径重新加载 `c_core.py`，正常情况刷新页面就恢复。
如果仍然报错，说明磁盘上的 `c_core.py` 没更新，或者进程确实需要重启：`Ctrl + C` 关掉后重新双击 `start.bat`
（顺手删掉 `__pycache__` 目录也可以）。

**想看 C 到底返回了什么**：每个实体卡片底部有「查看 C 层原始返回」，会显示 `query_neighbors()` 的原始字符串和条数；问答页的「两点关系查询」会显示 BFS 跳数与 C 层耗时（µs），答辩演示很好用。

**地图不显示 / 只有地标没有底图**：底图来自 OpenStreetMap，需要联网；断网时地标与路线仍会绘制（这是有意设计的离线降级）。

**导出的不是 docx 而是 md**：说明当前 Python 环境没有 `python-docx`，执行
`.venv\Scripts\python.exe -m pip install -r requirements.txt` 安装后即可导出 `.docx`。

---

## 6. 文件一览

```
红脉智谱-RedTraceAI\
├─ 00-开始这里.md          ← 导航（一分钟上手 / 目录地图 / 改内容速查表）
├─ README.md               ← 本文件
├─ app.py                  ← 页面（问答 / 图谱 / 研学三个页面）
├─ c_core.py               ← C 邻接表的 Python 封装 + 热加载 + BFS 封装
├─ graph.c / graph.dll     ← C 语言邻接表：一跳查询 + BFS 最短路径
├─ custom_route.py         ← AI 定制路线（图谱推荐算法）
├─ ui_graph.py             ← canvas 力导向图 + 时间轴（无第三方依赖）
├─ ui_map.py               ← Leaflet 研学地图（内联，离线可用）
├─ report.py               ← 研学小结导出（docx，缺依赖时退化为 md）
├─ kg.json                 ← 实体与关系【你要改的地方】
├─ materials/              ← 每个实体的 Markdown 资料（中英各一份）【你要改的地方】
├─ assets/                 ← 配图 + 背景图【你要改的地方】
├─ content/                ← 研学路线 / 题库 / 时间轴【你要改的地方】
├─ static/                 ← leaflet.js / leaflet.css（地图离线用）
├─ 文档/                    ← 01-架构速览.md / 02-代码与文件清单.md / 原始资料/
├─ nodes.txt / edges.txt   ← 自动生成，别手改
├─ _runtime/               ← 自动生成的 DLL 副本，可删
├─ .streamlit/config.toml  ← 配色主题
├─ 启动红脉智谱.bat          ← 双击启动
└─ 安装运行环境.bat          ← 换机器时先跑一次
```
