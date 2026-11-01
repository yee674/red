# -*- coding: utf-8 -*-
"""知识图谱交互组件（不依赖任何外部库）。

设计目标（对应课程验收与用户反馈）：
1. 可点击：点节点 → 右侧详情卡（图片、简介、双向关系，关系行可继续点）；
2. 可探索：搜索、类型筛选、缩放/平移、邻居聚焦、以节点为中心；
3. 可讲解：两点最短关系路径（在浏览器里做 BFS，路径逐边高亮）；
4. 离线可用：纯 Canvas + 原生 JS，不加载 ECharts / D3 / vis.js；
5. 双主题：颜色由组件参数注入，深色 / 亮色各自一套，不依赖字符串替换。
"""
from __future__ import annotations

import json

TYPE_COLORS = {
    "PERSON": "#e8b45c",
    "PLACE": "#6fbf8b",
    "EVENT": "#e2704b",
    "ORG": "#6fa8dc",
    "CONCEPT": "#b98ad4",
    "WORK": "#d69b83",
}

UI_TEXT = {
    "zh": {
        "search": "搜索实体…",
        "reset": "重置",
        "relayout": "重排",
        "path": "两点路径",
        "path_start": "请点选路径起点",
        "path_end": "再点选终点",
        "path_none": "两点之间没有连通路径",
        "path_done": "最短关系路径",
        "hops": "跳",
        "close": "关闭",
        "center": "以此为中心",
        "neighbors": "全部关系",
        "out": "指出",
        "in": "指入",
        "degree": "条关系",
        "focus": "点击节点查看详情 · 滚轮缩放 · 拖拽平移",
        "no_img": "暂无实拍图",
        "filter_all": "全部",
        "stats": "实体",
        "edges": "关系",
        "type": "类型",
    },
    "en": {
        "search": "Search entities…",
        "reset": "Reset",
        "relayout": "Re-layout",
        "path": "Shortest path",
        "path_start": "Pick a start node",
        "path_end": "Now pick a target node",
        "path_none": "No connecting path",
        "path_done": "Shortest relation path",
        "hops": "hops",
        "close": "Close",
        "center": "Centre here",
        "neighbors": "All relations",
        "out": "Outgoing",
        "in": "Incoming",
        "degree": "relations",
        "focus": "Click a node for details · scroll to zoom · drag to pan",
        "no_img": "No field photo",
        "filter_all": "All",
        "stats": "entities",
        "edges": "relations",
        "type": "Type",
    },
}

PALETTE = {
    "dark": {
        "bg": "rgba(24,11,13,.96)",
        "panel": "rgba(24,10,12,.97)",
        "panel2": "rgba(46,22,24,.96)",
        "text": "#f7efe8",
        "muted": "#cfb6ae",
        "line": "rgba(232,192,125,.20)",
        "edge": "rgba(232,192,125,.32)",
        "edge_on": "rgba(255,214,140,.95)",
        "gold": "#e8c07d",
        "chip": "rgba(232,192,125,.12)",
        "shadow": "rgba(0,0,0,.35)",
        "canvas": "rgba(18,8,10,.30)",
        "dot": "rgba(232,192,125,.10)",
    },
    "light": {
        "bg": "rgba(255,255,255,.82)",
        "panel": "#ffffff",
        "panel2": "#fdf7f2",
        "text": "#1f2430",
        "muted": "#48515e",
        "line": "rgba(31,36,48,.14)",
        "edge": "rgba(120,90,50,.34)",
        "edge_on": "rgba(164,97,26,.95)",
        "gold": "#a4611a",
        "chip": "rgba(164,97,26,.10)",
        "shadow": "rgba(31,36,48,.14)",
        "canvas": "#fbfaf8",
        "dot": "rgba(31,36,48,.10)",
    },
}


def _esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def graph_component(nodes: list[dict], edges: list[dict], legend: dict,
                    hint: str = "", height: int = 700, lang: str = "zh",
                    theme: str = "dark") -> str:
    """生成可点击知识图谱的完整 HTML。

    nodes: [{id, label, type, desc, img}]
    edges: [{s, t, rel}]
    legend: {TYPE: 本地化类型名}
    """
    ui = UI_TEXT.get(lang, UI_TEXT["zh"])
    pal = PALETTE.get(theme, PALETTE["dark"])
    payload = {
        "nodes": nodes, "edges": edges, "colors": TYPE_COLORS, "legend": legend,
        "ui": ui, "pal": pal, "hint": hint,
    }
    tokens = {
        "__SEARCH__": ui["search"], "__PATH__": ui["path"], "__RELAYOUT__": ui["relayout"],
        "__RESET__": ui["reset"], "__CENTER__": ui["center"], "__NEIGHBORS__": ui["neighbors"],
        "__CLOSE__": ui["close"], "__HINT__": hint or ui["focus"],
        "__LINE__": pal["line"], "__BG__": pal["bg"], "__SHADOW__": pal["shadow"],
        "__TEXT__": pal["text"], "__DOT__": pal["dot"], "__GOLD__": pal["gold"],
        "__PANEL__": pal["panel"], "__PANEL2__": pal["panel2"], "__MUTED__": pal["muted"],
        "__CHIP__": pal["chip"],
    }
    doc = _TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    doc = doc.replace("__HEIGHT__", str(height))
    for key, value in tokens.items():
        doc = doc.replace(key, str(value))
    return doc


_TEMPLATE = r"""
<div class="kg-shell" id="kg-shell">
  <canvas id="kg"></canvas>

  <div class="kg-top">
    <div class="kg-searchbox">
      <span class="kg-ico">⌕</span>
      <input id="kg-search" autocomplete="off" spellcheck="false" placeholder="__SEARCH__">
      <div class="kg-suggest" id="kg-suggest"></div>
    </div>
    <div class="kg-actions">
      <button class="kg-btn" id="kg-path" title="__PATH__">↔ <span>__PATH__</span></button>
      <button class="kg-btn" id="kg-relayout" title="__RELAYOUT__">↻ <span>__RELAYOUT__</span></button>
      <button class="kg-btn" id="kg-reset" title="__RESET__">⌂ <span>__RESET__</span></button>
    </div>
    <div class="kg-stat" id="kg-stat"></div>
  </div>

  <div class="kg-legend" id="kg-legend"></div>
  <div class="kg-tip" id="kg-tip"></div>

  <aside class="kg-panel" id="kg-panel">
    <button class="kg-x" id="kg-close" title="__CLOSE__">×</button>
    <div class="kg-photo" id="kg-photo"></div>
    <div class="kg-pbody">
      <div class="kg-pname" id="kg-pname"></div>
      <div class="kg-pmeta"><span class="kg-chip" id="kg-ptype"></span><span id="kg-pdeg"></span></div>
      <p class="kg-desc" id="kg-pdesc"></p>
      <div class="kg-reltitle" id="kg-reltitle">__NEIGHBORS__</div>
      <div id="kg-rels"></div>
      <div class="kg-pfoot">
        <button class="kg-btn broad" id="kg-center">◎ <span>__CENTER__</span></button>
      </div>
    </div>
  </aside>

  <div class="kg-pathbar" id="kg-pathbar">
    <b id="kg-pathlabel"></b><span id="kg-pathchain"></span>
    <button class="kg-x2" id="kg-pathclose">×</button>
  </div>

  <div class="kg-hint" id="kg-hint">__HINT__</div>
</div>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: transparent; }
  .kg-shell {
    position: relative; width: 100%; height: __HEIGHT__px; overflow: hidden;
    border-radius: 20px; border: 1px solid __LINE__;
    background: __BG__;
    box-shadow: 0 18px 46px __SHADOW__;
    font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
    color: __TEXT__; user-select: none;
  }
  .kg-shell::before {
    content: ""; position: absolute; inset: 0; pointer-events: none;
    background-image: radial-gradient(__DOT__ 1px, transparent 1px);
    background-size: 22px 22px; opacity: .55;
  }
  #kg { position: absolute; inset: 0; width: 100%; height: 100%; display: block; cursor: grab; }

  /* ---------- 顶部工具条 ---------- */
  .kg-top {
    position: absolute; left: 12px; right: 12px; top: 12px; z-index: 8;
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    pointer-events: none;
  }
  .kg-searchbox { position: relative; pointer-events: auto; }
  .kg-ico {
    position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
    color: __GOLD__; font-size: 15px; opacity: .9;
  }
  #kg-search {
    width: 210px; height: 36px; padding: 0 12px 0 30px;
    border-radius: 999px; border: 1px solid __LINE__;
    background: __PANEL2__; color: __TEXT__; outline: none;
    font: 13px/1 "Microsoft YaHei", sans-serif;
    box-shadow: 0 6px 18px __SHADOW__;
  }
  #kg-search:focus { border-color: __GOLD__; }
  #kg-search::placeholder { color: __MUTED__; opacity: .8; }
  .kg-suggest {
    position: absolute; left: 0; top: 42px; width: 250px; max-height: 260px;
    overflow: auto; border-radius: 12px; border: 1px solid __LINE__;
    background: __PANEL__; box-shadow: 0 16px 34px __SHADOW__;
    display: none; padding: 5px;
  }
  .kg-suggest.open { display: block; }
  .kg-suggest div {
    padding: 7px 10px; border-radius: 8px; cursor: pointer; font-size: 13px;
    display: flex; justify-content: space-between; gap: 8px;
  }
  .kg-suggest div:hover, .kg-suggest div.on { background: __CHIP__; }
  .kg-suggest small { color: __MUTED__; font-size: 11px; }

  .kg-actions { display: flex; gap: 6px; pointer-events: auto; margin-left: auto; }
  .kg-btn {
    height: 34px; padding: 0 12px; border-radius: 999px; cursor: pointer;
    border: 1px solid __LINE__; background: __PANEL2__; color: __TEXT__;
    font: 12.5px/1 "Microsoft YaHei", sans-serif; transition: all .16s ease;
    backdrop-filter: blur(8px);
  }
  .kg-btn:hover { border-color: __GOLD__; color: __GOLD__; transform: translateY(-1px); }
  .kg-btn.on { border-color: __GOLD__; background: __CHIP__; color: __GOLD__; }
  .kg-stat {
    width: 100%; text-align: right; color: __MUTED__; font-size: 11.5px;
    text-shadow: 0 1px 2px __SHADOW__;
  }

  /* ---------- 图例（可点击筛选） ---------- */
  .kg-legend {
    position: absolute; left: 14px; bottom: 12px; z-index: 7;
    display: flex; flex-wrap: wrap; gap: 6px; max-width: calc(100% - 28px);
  }
  .kg-legend button {
    display: inline-flex; align-items: center; gap: 5px; cursor: pointer;
    border: 1px solid __LINE__; background: __PANEL2__; color: __MUTED__;
    border-radius: 999px; padding: 4px 10px; font: 11.5px/1 "Microsoft YaHei", sans-serif;
    opacity: .95; transition: all .15s;
  }
  .kg-legend button i { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
  .kg-legend button.off { opacity: .35; text-decoration: line-through; }
  .kg-legend button:hover { border-color: __GOLD__; }

  /* ---------- 悬浮提示 ---------- */
  .kg-tip {
    position: absolute; z-index: 9; pointer-events: none; opacity: 0;
    transform: translate(-50%, -120%); transition: opacity .12s;
    background: __PANEL__; border: 1px solid __LINE__; color: __TEXT__;
    border-radius: 10px; padding: 7px 11px; font-size: 12.5px; line-height: 1.55;
    box-shadow: 0 12px 28px __SHADOW__; max-width: 260px; text-align: center;
  }
  .kg-tip b { color: __GOLD__; }
  .kg-tip small { color: __MUTED__; display: block; }

  /* ---------- 右侧详情卡 ---------- */
  .kg-panel {
    position: absolute; top: 52px; right: 12px; bottom: 44px; width: 306px;
    z-index: 10; border-radius: 16px; border: 1px solid __LINE__;
    background: linear-gradient(180deg, __PANEL__, __PANEL2__);
    box-shadow: 0 20px 44px __SHADOW__; overflow: auto;
    transform: translateX(calc(100% + 24px)); opacity: 0;
    transition: transform .22s ease, opacity .22s ease;
  }
  .kg-panel.open { transform: translateX(0); opacity: 1; }
  .kg-x {
    position: absolute; right: 8px; top: 8px; z-index: 3; width: 26px; height: 26px;
    border-radius: 50%; border: 1px solid __LINE__; background: __PANEL__;
    color: __MUTED__; cursor: pointer; font-size: 16px; line-height: 1;
  }
  .kg-x:hover { color: __GOLD__; border-color: __GOLD__; }
  .kg-photo {
    height: 148px; background-size: cover; background-position: center;
    background-color: __CHIP__; border-bottom: 1px solid __LINE__;
  }
  .kg-photo.empty { display: flex; align-items: center; justify-content: center;
    color: __MUTED__; font-size: 12px; }
  .kg-pbody { padding: 12px 14px 16px; }
  .kg-pname { font-size: 18px; font-weight: 700; color: __TEXT__; line-height: 1.35; padding-right: 20px; }
  .kg-pmeta { display: flex; align-items: center; gap: 8px; margin: 7px 0 9px;
    color: __MUTED__; font-size: 11.5px; }
  .kg-chip { color: __GOLD__; border: 1px solid __LINE__; background: __CHIP__;
    border-radius: 999px; padding: 3px 8px; }
  .kg-desc { margin: 0 0 10px; color: __MUTED__; font-size: 12.5px; line-height: 1.7; }
  .kg-reltitle { font-size: 11px; letter-spacing: .1em; color: __GOLD__; opacity: .9;
    margin: 10px 0 6px; text-transform: uppercase; }
  .kg-rel {
    display: flex; align-items: flex-start; gap: 7px; padding: 7px 8px; margin-bottom: 4px;
    border-radius: 9px; border: 1px solid transparent; cursor: pointer;
    font-size: 12.5px; line-height: 1.5; transition: all .14s;
  }
  .kg-rel:hover { background: __CHIP__; border-color: __LINE__; }
  .kg-rel .dir { color: __GOLD__; font-size: 11px; flex: 0 0 auto; margin-top: 1px; }
  .kg-rel .who { color: __TEXT__; }
  .kg-rel .relname { color: __MUTED__; font-size: 11px; }
  .kg-pfoot { margin-top: 12px; }
  .kg-btn.broad { width: 100%; height: 34px; }

  /* ---------- 路径条 ---------- */
  .kg-pathbar {
    position: absolute; left: 50%; bottom: 54px; transform: translate(-50%, 20px);
    z-index: 11; display: none; align-items: center; gap: 9px; max-width: calc(100% - 40px);
    background: __PANEL__; border: 1px solid __GOLD__; border-radius: 999px;
    padding: 7px 12px; box-shadow: 0 14px 30px __SHADOW__;
    font-size: 12.5px; color: __TEXT__; opacity: 0; transition: all .2s;
  }
  .kg-pathbar.open { display: flex; transform: translate(-50%, 0); opacity: 1; }
  .kg-pathbar b { color: __GOLD__; flex: 0 0 auto; }
  .kg-pathbar span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .kg-x2 { border: 0; background: transparent; color: __MUTED__; cursor: pointer; font-size: 15px; }
  .kg-x2:hover { color: __GOLD__; }

  .kg-hint {
    position: absolute; right: 14px; bottom: 12px; z-index: 6; color: __MUTED__;
    font-size: 11px; text-shadow: 0 1px 2px __SHADOW__; max-width: 46%;
    text-align: right; opacity: .9; pointer-events: none;
  }
  @media (max-width: 720px) {
    .kg-panel { width: min(300px, calc(100% - 24px)); top: auto; height: 360px; }
    #kg-search { width: 150px; }
    .kg-actions .kg-btn span { display: none; }
    .kg-hint { display: none; }
  }
</style>
<script>
(function () {
  const DATA = __DATA__;
  const T = DATA.ui, P = DATA.pal;
  const cv = document.getElementById("kg");
  const ctx = cv.getContext("2d");
  const shell = document.getElementById("kg-shell");
  const tip = document.getElementById("kg-tip");
  const panel = document.getElementById("kg-panel");
  const suggest = document.getElementById("kg-suggest");
  const search = document.getElementById("kg-search");
  const pathbar = document.getElementById("kg-pathbar");

  document.getElementById("kg-search").placeholder = T.search;
  document.getElementById("kg-hint").textContent = DATA.hint || T.focus;
  document.getElementById("kg-pathlabel").textContent = T.path_done;
  document.getElementById("kg-path").querySelector("span").textContent = T.path;
  document.getElementById("kg-relayout").querySelector("span").textContent = T.relayout;
  document.getElementById("kg-reset").querySelector("span").textContent = T.reset;
  document.getElementById("kg-center").querySelector("span").textContent = T.center;
  document.getElementById("kg-reltitle").textContent = T.neighbors;
  document.getElementById("kg-close").title = T.close;
  document.querySelector(".kg-stat").textContent =
    DATA.nodes.length + " " + T.stats + " · " + DATA.edges.length + " " + T.edges;

  // ---------- 数据 ----------
  const idx = {};
  const nodes = DATA.nodes.map((n, i) => {
    idx[n.id] = i;
    const a = (i / DATA.nodes.length) * Math.PI * 2 + 0.4;
    const rad = Math.min(window.innerWidth, 640) * 0.32;
    return Object.assign({}, n, {
      x: Math.cos(a) * rad + (Math.random() - .5) * 40,
      y: Math.sin(a) * rad + (Math.random() - .5) * 40,
      vx: 0, vy: 0, deg: 0,
    });
  });
  const links = DATA.edges.map(e => ({ a: idx[e.s], b: idx[e.t], rel: e.rel }))
    .filter(l => l.a !== undefined && l.b !== undefined);
  links.forEach(l => { nodes[l.a].deg++; nodes[l.b].deg++; });

  const adj = nodes.map(() => []);
  links.forEach(l => { adj[l.a].push(l.b); adj[l.b].push(l.a); });

  // ---------- 视图 ----------
  let W = 1, H = 1, dpr = Math.min(2, window.devicePixelRatio || 1);
  const cam = { x: 0, y: 0, k: 1 };
  let alpha = 1, hover = -1, selected = -1, dragNode = null, panning = false;
  let moved = false, lastX = 0, lastY = 0, userMoved = false;
  const hiddenTypes = new Set();
  let pathMode = false, pathA = -1, pathB = -1, pathEdges = new Set(), pathNodes = new Set();

  function resize() {
    const r = shell.getBoundingClientRect();
    W = Math.max(320, r.width); H = Math.max(320, r.height);
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    cam.k = W < 760 ? 0.8 : 1;
  }
  window.addEventListener("resize", () => { resize(); });

  const nrad = n => 10 + Math.min(n.deg, 10) * 1.05;

  // ---------- 力导向 ----------
  function tick() {
    if (alpha > 0.018) {
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const m = nodes[j];
          let dx = n.x - m.x, dy = n.y - m.y;
          let d2 = dx * dx + dy * dy || 0.01;
          if (d2 < 120000) {
            const d = Math.sqrt(d2);
            const f = 3200 / d2;
            const fx = dx / d * f, fy = dy / d * f;
            n.vx += fx; n.vy += fy; m.vx -= fx; m.vy -= fy;
          }
        }
        n.vx -= n.x * 0.0016; n.vy -= n.y * 0.0016;
      }
      links.forEach(l => {
        const a = nodes[l.a], b = nodes[l.b];
        let dx = b.x - a.x, dy = b.y - a.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const target = 180;
        const f = (d - target) * 0.0125;
        const fx = dx / d * f, fy = dy / d * f;
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
      });
      nodes.forEach(n => {
        n.vx *= 0.86; n.vy *= 0.86;
        n.x += n.vx * alpha; n.y += n.vy * alpha;
      });
      // 防重叠
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = b.x - a.x, dy = b.y - a.y;
          const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
          const min = nrad(a) + nrad(b) + 30;
          if (d < min) {
            const push = (min - d) / d * 0.34;
            a.x -= dx * push; a.y -= dy * push;
            b.x += dx * push; b.y += dy * push;
          }
        }
      }
      alpha *= 0.985;
      if (alpha < 0.018) alpha = 0.018;
    }
  }

  // ---------- 绘制 ----------
  function worldOf(ev) {
    const r = cv.getBoundingClientRect();
    return {
      x: (ev.clientX - r.left - W / 2 - cam.x) / cam.k,
      y: (ev.clientY - r.top - H / 2 - cam.y) / cam.k,
      sx: ev.clientX - r.left, sy: ev.clientY - r.top,
    };
  }

  function draw() {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.translate(W / 2 + cam.x, H / 2 + cam.y);
    ctx.scale(cam.k, cam.k);

    const active = selected >= 0 ? selected : hover;
    const focus = new Set();
    if (active >= 0) { focus.add(active); (adj[active] || []).forEach(i => focus.add(i)); }

    // 边
    links.forEach(l => {
      const a = nodes[l.a], b = nodes[l.b];
      const hidden = hiddenTypes.has(a.type) || hiddenTypes.has(b.type);
      const on = active < 0 || (focus.has(l.a) && focus.has(l.b));
      const inPath = pathEdges.has(l.a + "-" + l.b) || pathEdges.has(l.b + "-" + l.a);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
      if (inPath) {
        ctx.strokeStyle = P.edge_on; ctx.lineWidth = 2.6 / cam.k;
      } else {
        ctx.strokeStyle = on ? P.edge : "rgba(150,130,120,.10)";
        ctx.lineWidth = (on ? 1.15 : 0.7) / cam.k;
      }
      ctx.globalAlpha = hidden ? 0.06 : (on ? 0.95 : 0.22);
      ctx.stroke(); ctx.globalAlpha = 1;

      // 箭头（方向感）
      if (!hidden && (on || inPath)) {
        const mx = a.x + (b.x - a.x) * 0.56, my = a.y + (b.y - a.y) * 0.56;
        const ang = Math.atan2(b.y - a.y, b.x - a.x);
        const s = (inPath ? 7 : 5.5) / cam.k;
        ctx.beginPath();
        ctx.moveTo(mx, my);
        ctx.lineTo(mx - Math.cos(ang - 0.42) * s, my - Math.sin(ang - 0.42) * s);
        ctx.moveTo(mx, my);
        ctx.lineTo(mx - Math.cos(ang + 0.42) * s, my - Math.sin(ang + 0.42) * s);
        ctx.strokeStyle = inPath ? P.edge_on : P.edge;
        ctx.globalAlpha = inPath ? 1 : 0.55;
        ctx.stroke(); ctx.globalAlpha = 1;
      }

      // 选中节点的关系标签
      if (((hover >= 0 && (l.a === hover || l.b === hover)) || inPath) && !hidden) {
        const mx = a.x + (b.x - a.x) * 0.5, my = a.y + (b.y - a.y) * 0.5;
        ctx.font = "11px 'Microsoft YaHei', sans-serif";
        const text = l.rel;
        const tw = ctx.measureText(text).width + 12;
        ctx.fillStyle = P.panel; ctx.globalAlpha = 0.92;
        ctx.beginPath();
        ctx.roundRect(mx - tw / 2, my - 9, tw, 18, 9);
        ctx.fill(); ctx.globalAlpha = 1;
        ctx.strokeStyle = P.line; ctx.lineWidth = 1 / cam.k; ctx.stroke();
        ctx.fillStyle = P.gold; ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(text, mx, my);
      }
    });

    // 节点
    nodes.forEach((n, i) => {
      const hidden = hiddenTypes.has(n.type);
      const on = active < 0 || focus.has(i);
      const r = nrad(n) + (i === active ? 2 : 0);
      ctx.globalAlpha = hidden ? 0.10 : (on ? 1 : 0.28);

      if (i === selected || i === hover || pathNodes.has(i)) {
        ctx.beginPath(); ctx.arc(n.x, n.y, r + 8 / cam.k, 0, Math.PI * 2);
        ctx.fillStyle = DATA.colors[n.type] || "#999";
        ctx.globalAlpha = hidden ? 0.08 : 0.16; ctx.fill();
        ctx.globalAlpha = hidden ? 0.10 : (on ? 1 : 0.28);
      }

      const grd = ctx.createRadialGradient(n.x - r * .35, n.y - r * .35, r * .15, n.x, n.y, r);
      grd.addColorStop(0, "#fff4dd");
      grd.addColorStop(0.28, DATA.colors[n.type] || "#999");
      grd.addColorStop(1, "#8d3f2a");
      ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = grd; ctx.fill();
      ctx.lineWidth = (i === selected ? 2.6 : 1.3) / cam.k;
      ctx.strokeStyle = i === selected ? "#fff3d8" : "rgba(20,8,10,.55)";
      ctx.stroke();

      if (pathNodes.has(i)) {
        ctx.beginPath(); ctx.arc(n.x, n.y, r + 5 / cam.k, 0, Math.PI * 2);
        ctx.strokeStyle = "#ffd27a"; ctx.lineWidth = 2 / cam.k; ctx.stroke();
      }

      ctx.globalAlpha = 1;
    });

    // 标签防重叠：活跃/悬浮优先，其次按度数从高到低；放不下的标签只留到 hover 时显示
    const placed = [];
    const order = nodes.map((n, i) => i).sort((a, b) => {
      const pa = (a === active ? 1000 : 0) + nodes[a].deg;
      const pb = (b === active ? 1000 : 0) + nodes[b].deg;
      return pb - pa;
    });
    order.forEach(i => {
      const n = nodes[i];
      if (hiddenTypes.has(n.type) && i !== active) return;
      const r = nrad(n);
      ctx.font = (i === active ? "700 14.5px" : "13px") + " 'Microsoft YaHei', sans-serif";
      const tw = ctx.measureText(n.label).width + 10 / cam.k;
      const th = 19 / cam.k;
      const cx = n.x, cy = n.y + r + 13 / cam.k;
      const box = { x: cx - tw / 2, y: cy - th / 2, w: tw, h: th };
      const hit = placed.some(q => !(box.x + box.w < q.x - 2 / cam.k || box.x > q.x + q.w + 2 / cam.k ||
                                     box.y + box.h < q.y - 1 / cam.k || box.y > q.y + q.h + 1 / cam.k));
      if (hit && i !== active && i !== hover) return;
      placed.push(box);
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.lineWidth = 4.5 / cam.k;
      ctx.strokeStyle = P.panel;
      ctx.strokeText(n.label, cx, cy);
      ctx.fillStyle = i === active ? P.text : P.muted;
      ctx.fillText(n.label, cx, cy);
    });
    ctx.restore();
  }

  function loop() { tick(); draw(); requestAnimationFrame(loop); }

  // ---------- 悬浮提示 / 拾取 ----------
  function pick(p) {
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i];
      const r = nrad(n) + 6 / cam.k;
      if ((p.x - n.x) ** 2 + (p.y - n.y) ** 2 <= r * r) return i;
    }
    return -1;
  }

  cv.addEventListener("pointermove", ev => {
    const p = worldOf(ev);
    if (dragNode !== null) {
      const n = nodes[dragNode];
      n.x = p.x; n.y = p.y; n.vx = n.vy = 0; moved = true; alpha = 0.35;
      return;
    }
    if (panning) {
      cam.x += ev.clientX - lastX; cam.y += ev.clientY - lastY;
      lastX = ev.clientX; lastY = ev.clientY; moved = true;
      return;
    }
    hover = pick(p);
    cv.style.cursor = hover >= 0 ? "pointer" : "grab";
    if (hover >= 0) {
      const n = nodes[hover];
      tip.style.opacity = 1;
      tip.innerHTML = "<b>" + esc(n.label) + "</b><small>" + esc(n.typeLabel || n.type) +
        " · " + n.deg + " " + T.degree + " · " + esc(T.focus.split("·")[0].trim()) + "</small>";
      tip.style.left = p.sx + "px"; tip.style.top = p.sy + "px";
    } else {
      tip.style.opacity = 0;
    }
  });

  cv.addEventListener("pointerdown", ev => {
    userMoved = true;
    const p = worldOf(ev);
    const hit = pick(p);
    if (hit >= 0) { dragNode = hit; moved = false; }
    else { panning = true; moved = false; lastX = ev.clientX; lastY = ev.clientY; cv.style.cursor = "grabbing"; }
    cv.setPointerCapture(ev.pointerId);
  });

  cv.addEventListener("pointerup", ev => {
    const p = worldOf(ev);
    if (dragNode !== null) {
      const i = dragNode;
      dragNode = null;
      if (!moved) handleClick(i);
    } else if (panning) {
      panning = false; cv.style.cursor = "grab";
      if (!moved) handleClick(-1);
    }
    cv.releasePointerCapture(ev.pointerId);
  });

  cv.addEventListener("wheel", ev => {
    ev.preventDefault(); userMoved = true;
    const r = cv.getBoundingClientRect();
    const mx = ev.clientX - r.left, my = ev.clientY - r.top;
    const wx = (mx - W / 2 - cam.x) / cam.k, wy = (my - H / 2 - cam.y) / cam.k;
    const k = Math.max(0.45, Math.min(2.6, cam.k * (ev.deltaY < 0 ? 1.12 : 0.89)));
    cam.k = k;
    cam.x = mx - W / 2 - wx * k; cam.y = my - H / 2 - wy * k;
  }, { passive: false });

  cv.addEventListener("dblclick", () => resetView());

  // ---------- 交互逻辑 ----------
  function handleClick(i) {
    if (i < 0) { closePanel(); return; }
    if (pathMode) {
      if (pathA < 0) { pathA = i; pathB = -1; pathNodes = new Set([i]); pathEdges = new Set();
        setPathStatus(T.path_end); return; }
      if (i === pathA) return;
      pathB = i;
      const res = bfs(pathA, pathB);
      if (!res) { setPathStatus(T.path_none); pathNodes = new Set([pathA, pathB]); return; }
      pathNodes = new Set(res.nodes); pathEdges = new Set(res.edges);
      showPath(res);
      selected = i; openPanel(i);
      pathMode = false;
      document.getElementById("kg-path").classList.remove("on");
      return;
    }
    selected = i; openPanel(i);
  }

  function bfs(s, t) {
    const prev = new Array(nodes.length).fill(-1);
    const prevEdge = new Array(nodes.length).fill(null);
    const q = [s]; const seen = new Set([s]);
    while (q.length) {
      const u = q.shift();
      if (u === t) break;
      for (let k = 0; k < adj[u].length; k++) {
        const v = adj[u][k];
        if (!seen.has(v)) { seen.add(v); prev[v] = u; q.push(v); }
      }
    }
    if (!seen.has(t)) return null;
    const seq = []; const es = [];
    let cur = t;
    while (cur !== s) { seq.push(cur); cur = prev[cur]; }
    seq.push(s); seq.reverse();
    for (let i = 0; i + 1 < seq.length; i++) {
      const a = seq[i], b = seq[i + 1];
      const l = links.find(x => (x.a === a && x.b === b) || (x.a === b && x.b === a));
      es.push(a + "-" + b);
      seq[i] = { i: a, label: nodes[a].label, rel: l ? l.rel : "" };
    }
    seq[seq.length - 1] = { i: t, label: nodes[t].label, rel: "" };
    return { nodes: seq.map(x => x.i), edges: es, chain: seq };
  }

  function showPath(res) {
    pathbar.classList.add("open");
    document.getElementById("kg-pathlabel").textContent = T.path_done + " · " + (res.nodes.length - 1) + " " + T.hops;
    document.getElementById("kg-pathchain").textContent =
      res.chain.map((x, n) => n === 0 ? x.label : " —" + x.rel + "→ " + x.label).join("");
    panel.classList.remove("open");
  }
  function setPathStatus(text) {
    pathbar.classList.add("open");
    document.getElementById("kg-pathlabel").textContent = text;
    document.getElementById("kg-pathchain").textContent = "";
  }

  function openPanel(i) {
    const n = nodes[i];
    document.getElementById("kg-pname").textContent = n.label;
    document.getElementById("kg-ptype").textContent = n.typeLabel || n.type;
    document.getElementById("kg-pdeg").textContent = n.deg + " " + T.degree;
    document.getElementById("kg-pdesc").textContent = n.desc || "";
    const ph = document.getElementById("kg-photo");
    if (n.img) {
      ph.classList.remove("empty");
      ph.style.backgroundImage = 'url("' + n.img + '")';
    } else {
      ph.classList.add("empty");
      ph.style.backgroundImage = "none";
      ph.textContent = T.no_img;
    }
    const rels = [];
    links.forEach(l => {
      if (l.a === i) rels.push({ dir: "→", other: l.b, rel: l.rel });
      else if (l.b === i) rels.push({ dir: "←", other: l.a, rel: l.rel });
    });
    const box = document.getElementById("kg-rels");
    box.innerHTML = rels.length ? rels.map(r =>
      '<div class="kg-rel" data-id="' + nodes[r.other].id + '">' +
      '<span class="dir">' + r.dir + '</span><span class="who">' + esc(nodes[r.other].label) +
      '</span><span class="relname">' + esc(r.rel) + '</span></div>').join("")
      : '<div class="kg-rel"><span class="who">' + esc(T.degree) + " 0</span></div>";
    box.querySelectorAll(".kg-rel[data-id]").forEach(el => {
      el.addEventListener("click", () => {
        const j = idx[el.dataset.id];
        if (j !== undefined) { selected = j; openPanel(j); centreOn(j); }
      });
    });
    panel.classList.add("open");
    if (pathMode) { pathMode = false; document.getElementById("kg-path").classList.remove("on"); }
  }

  function closePanel() { panel.classList.remove("open"); selected = -1; }

  function centreOn(i) {
    const n = nodes[i];
    cam.k = Math.max(cam.k, 1);
    const panelW = panel.classList.contains("open") ? Math.min(320, W * 0.45) : 0;
    cam.x = (W - panelW) / 2 - W / 2 - n.x * cam.k;
    cam.y = H / 2 - H / 2 - n.y * cam.k + 10;
  }

  function resetView() {
    userMoved = false;
    selected = -1; pathA = pathB = -1; pathMode = false;
    pathEdges = new Set(); pathNodes = new Set(); hiddenTypes.clear();
    closePanel(); pathbar.classList.remove("open");
    document.getElementById("kg-path").classList.remove("on");
    cam.x = 0; cam.y = 0; cam.k = W < 760 ? 0.8 : 1;
    alpha = 0.6;
    renderLegend();
  }

  // ---------- 图例筛选 ----------
  const legend = document.getElementById("kg-legend");
  function renderLegend() {
    legend.innerHTML = "";
    Object.keys(DATA.legend).forEach(type => {
      const b = document.createElement("button");
      b.innerHTML = '<i style="background:' + (DATA.colors[type] || "#888") + '"></i>' +
        esc(DATA.legend[type]);
      if (hiddenTypes.has(type)) b.classList.add("off");
      b.addEventListener("click", () => {
        if (hiddenTypes.has(type)) hiddenTypes.delete(type); else hiddenTypes.add(type);
        renderLegend();
      });
      legend.appendChild(b);
    });
  }
  renderLegend();

  // ---------- 搜索 ----------
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function renderSuggest(q) {
    const hits = nodes.map((n, i) => ({ n, i }))
      .filter(o => !q || o.n.label.toLowerCase().includes(q.toLowerCase()) ||
        o.n.id.toLowerCase().includes(q.toLowerCase()))
      .slice(0, 8);
    suggest.innerHTML = hits.length ? hits.map(o =>
      '<div data-i="' + o.i + '"><span>' + esc(o.n.label) + '</span><small>' +
      esc(o.n.typeLabel || o.n.type) + '</small></div>').join("")
      : '<div style="cursor:default;color:' + P.muted + '">—</div>';
    suggest.classList.add("open");
    suggest.querySelectorAll("[data-i]").forEach(el => {
      el.addEventListener("mousedown", ev => {
        ev.preventDefault();
        const i = Number(el.dataset.i);
        selected = i; openPanel(i); centreOn(i); alpha = 0.45;
        search.value = nodes[i].label; suggest.classList.remove("open");
      });
    });
  }
  search.addEventListener("input", () => renderSuggest(search.value.trim()));
  search.addEventListener("focus", () => renderSuggest(search.value.trim()));
  search.addEventListener("blur", () => setTimeout(() => suggest.classList.remove("open"), 120));
  search.addEventListener("keydown", ev => {
    if (ev.key === "Enter") {
      const first = suggest.querySelector("[data-i]");
      if (first) first.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    }
  });

  // ---------- 按钮 ----------
  document.getElementById("kg-close").addEventListener("click", closePanel);
  document.getElementById("kg-center").addEventListener("click", () => {
    if (selected >= 0) centreOn(selected);
  });
  document.getElementById("kg-reset").addEventListener("click", resetView);
  document.getElementById("kg-relayout").addEventListener("click", () => {
    nodes.forEach((n, i) => {
      const a = (i / nodes.length) * Math.PI * 2 + Math.random() * 0.5;
      const rad = Math.min(W, H) * (0.22 + Math.random() * 0.16);
      n.x = Math.cos(a) * rad; n.y = Math.sin(a) * rad; n.vx = n.vy = 0;
    });
    cam.x = 0; cam.y = 0; alpha = 1;
  });
  document.getElementById("kg-path").addEventListener("click", () => {
    pathMode = !pathMode;
    document.getElementById("kg-path").classList.toggle("on", pathMode);
    pathA = pathB = -1; pathEdges = new Set(); pathNodes = new Set();
    if (pathMode) setPathStatus(T.path_start);
    else pathbar.classList.remove("open");
  });
  document.getElementById("kg-pathclose").addEventListener("click", () => {
    pathbar.classList.remove("open"); pathEdges = new Set(); pathNodes = new Set();
    pathMode = false; document.getElementById("kg-path").classList.remove("on");
  });

  // ---------- 启动 ----------
  resize();
  // 初始把图铺满：等模拟稳定后按包围盒缩放；用户一旦操作就不再自动抢镜头
  function fitView() {
    if (userMoved) return;
    const pad = 72 / cam.k;
    const xs = nodes.map(n => n.x), ys = nodes.map(n => n.y);
    const minX = Math.min(...xs) - pad, maxX = Math.max(...xs) + pad;
    const minY = Math.min(...ys) - pad, maxY = Math.max(...ys) + pad + 26 / cam.k;
    cam.k = Math.max(0.6, Math.min(1.35, Math.min(W / (maxX - minX), (H - 54) / (maxY - minY))));
    cam.x = -((maxX + minX) / 2) * cam.k;
    cam.y = -((maxY + minY) / 2) * cam.k + 10;
  }
  setTimeout(fitView, 1300);
  setTimeout(fitView, 3600);
  window.__KG_DEBUG__ = {
    nodes: nodes.map((n, i) => ({ i: i, id: n.id, label: n.label })),
    select: i => { selected = i; openPanel(i); centreOn(i); draw(); },
    path: (a, b) => { pathA = a; pathB = b; const r = bfs(a, b); if (r) { pathNodes = new Set(r.nodes); pathEdges = new Set(r.edges); showPath(r); } },
    reset: resetView,
  };
  loop();
})();
</script>
"""


def timeline_html(items: list[dict], title: str = "") -> str:
    """时间轴：items = [{year, label, text, entity}]"""
    rows = []
    last_year = None
    for it in items:
        year = it["year"]
        show_year = year != last_year
        last_year = year
        rows.append(
            f'<div class="tl-row">'
            f'<div class="tl-year">{year if show_year else ""}</div>'
            f'<div class="tl-dot"></div>'
            f'<div class="tl-card"><div class="tl-label">{_esc(it["label"])}</div>'
            f'<div class="tl-text">{_esc(it.get("text", ""))}</div></div>'
            f'</div>'
        )
    return f"""
<div class="tl-wrap">
  {f'<div class="tl-title">{_esc(title)}</div>' if title else ''}
  <div class="tl-body">{''.join(rows)}</div>
</div>
<style>
  .tl-wrap {{ margin-top: .4rem; }}
  .tl-title {{ font: 600 15px/1.6 "Microsoft YaHei", sans-serif; color: var(--gold, #e8c07d); margin-bottom: .6rem; }}
  .tl-body {{ position: relative; padding-left: 8px; }}
  .tl-body::before {{ content: ""; position: absolute; left: 74px; top: 6px; bottom: 6px;
                     width: 2px; background: linear-gradient(180deg, rgba(232,192,125,.65), rgba(232,192,125,.12)); }}
  .tl-row {{ display: grid; grid-template-columns: 62px 18px 1fr; align-items: start;
            gap: 6px; margin-bottom: .55rem; }}
  .tl-year {{ font: 600 15px/1.5 "Microsoft YaHei", sans-serif; color: var(--gold, #e8c07d); text-align: right; }}
  .tl-dot {{ width: 9px; height: 9px; border-radius: 50%; background: #e8c07d;
            margin: 6px auto 0; box-shadow: 0 0 0 3px rgba(232,192,125,.16); }}
  .tl-card {{ background: rgba(255,255,255,.045); border: 1px solid rgba(232,192,125,.2);
             border-radius: 12px; padding: .5rem .75rem; }}
  .tl-label {{ font: 600 13.5px/1.5 "Microsoft YaHei", sans-serif; color: var(--ink, #f5ebe6); }}
  .tl-text {{ font: 12.5px/1.65 "Microsoft YaHei", sans-serif; color: var(--muted, #cdb7af); margin-top: 2px; }}
</style>
"""
