# -*- coding: utf-8 -*-
"""手绘校园地图组件：在城南 / 东方红校区手绘图上标出研学点位。

不依赖 Leaflet，也不依赖网络：地图图片 base64 内联，编号点位按百分比坐标定位，
点击编号弹出照片与讲解；支持缩放、拖拽、重置。
"""
from __future__ import annotations

import json

UI = {
    "zh": {"zoom_in": "放大", "zoom_out": "缩小", "reset": "复位", "close": "关闭",
           "hint": "点击编号看点位 · 滚轮缩放 · 拖拽平移", "stop": "第 {n} 站"},
    "en": {"zoom_in": "Zoom in", "zoom_out": "Zoom out", "reset": "Reset", "close": "Close",
           "hint": "Click a number for details · scroll to zoom · drag to pan", "stop": "Stop {n}"},
}


def map_component(pois: list[dict], map_uri: str, map_name: str, height: int = 520,
                  route_title: str = "", note: str = "", lang: str = "zh",
                  theme: str = "dark") -> str:
    ui = UI.get(lang, UI["zh"])
    data = []
    for i, p in enumerate(pois, 1):
        data.append({
            "i": i, "name": p["name"], "addr": p.get("addr", ""),
            "intro": p.get("intro", ""), "img": p.get("img", ""),
            "x": p["x"] * 100, "y": p["y"] * 100,
            "type": p.get("type", ""),
        })
    payload = json.dumps(data, ensure_ascii=False)
    return _TEMPLATE.replace("__DATA__", payload).replace("__MAP__", map_uri) \
        .replace("__MAPNAME__", map_name).replace("__TITLE__", route_title) \
        .replace("__NOTE__", note).replace("__HINT__", ui["hint"]) \
        .replace("__ZOOMIN__", ui["zoom_in"]).replace("__ZOOMOUT__", ui["zoom_out"]) \
        .replace("__RESET__", ui["reset"]) \
        .replace("__STOP__", ui["stop"]).replace("__HEIGHT__", str(height)) \
        .replace("__LANG__", lang)


_TEMPLATE = r"""
<div class="cm-wrap" id="cm-wrap">
  <div class="cm-canvas" id="cm-canvas">
    <div class="cm-stage" id="cm-stage">
      <img id="cm-map" src="__MAP__" alt="__MAPNAME__">
      <svg class="cm-svg" viewBox="0 0 1000 1000" preserveAspectRatio="none">
        <polyline id="cm-line" points="" fill="none" stroke="#c0392b"
                  stroke-width="5" stroke-dasharray="14 10" stroke-linecap="round"
                  vector-effect="non-scaling-stroke"></polyline>
      </svg>
      <div id="cm-pins"></div>
    </div>
  </div>

  <div class="cm-top">
    <div>
      <div class="cm-campus">__MAPNAME__</div>
      <div class="cm-title">__TITLE__</div>
    </div>
    <div class="cm-tools">
      <button id="cm-in" title="__ZOOMIN__">＋</button>
      <button id="cm-out" title="__ZOOMOUT__">－</button>
      <button id="cm-reset" title="__RESET__">⌂</button>
    </div>
  </div>

  <div class="cm-card" id="cm-card">
    <button class="cm-x" id="cm-close">×</button>
    <div class="cm-photo" id="cm-photo"></div>
    <div class="cm-body">
      <div class="cm-name" id="cm-name"></div>
      <div class="cm-addr" id="cm-addr"></div>
      <div class="cm-intro" id="cm-intro"></div>
    </div>
  </div>

  <div class="cm-foot">__HINT__<span>__NOTE__</span></div>
</div>
<style>
  .cm-wrap { position: relative; width: 100%; height: __HEIGHT__px; overflow: hidden;
    border-radius: 18px; border: 1px solid rgba(160,120,80,.35);
    background: #f6eee2; box-shadow: 0 14px 34px rgba(0,0,0,.18);
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }
  .cm-canvas { position: absolute; inset: 0; overflow: hidden; cursor: grab; touch-action: none; }
  .cm-stage { position: absolute; left: 50%; top: 50%; transform-origin: center center;
    transform: translate(-50%,-50%); will-change: transform; }
  .cm-stage img { display: block; width: 100%; height: 100%; user-select: none; -webkit-user-drag: none; }
  .cm-svg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
  .cm-top { position: absolute; left: 12px; top: 12px; right: 12px; z-index: 8;
    display: flex; justify-content: space-between; gap: 8px; pointer-events: none; }
  .cm-top > div:first-child { background: rgba(255,250,242,.92); border: 1px solid rgba(160,120,80,.35);
    border-radius: 12px; padding: 6px 11px; box-shadow: 0 6px 16px rgba(0,0,0,.12); }
  .cm-campus { font-size: 10px; letter-spacing: .14em; color: #9b6a2c; text-transform: uppercase; }
  .cm-title { font-size: 15px; font-weight: 700; color: #3a2418; margin-top: 1px; }
  .cm-tools { display: flex; gap: 5px; pointer-events: auto; }
  .cm-tools button, .cm-x { width: 30px; height: 30px; border-radius: 50%;
    border: 1px solid rgba(160,120,80,.4); background: rgba(255,250,242,.94);
    color: #7a4a12; font-size: 16px; line-height: 1; cursor: pointer; }
  .cm-tools button:hover { background: #f3e2c8; }
  .cm-pin { position: absolute; transform: translate(-50%,-50%); width: 30px; height: 30px;
    border-radius: 50%; border: 2px solid #fff8ec; background: linear-gradient(145deg,#c0392b,#e8a45a);
    color: #fff; font: 700 13px/26px "Microsoft YaHei",sans-serif; text-align: center;
    cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,.35); z-index: 4;
    transition: transform .15s ease, box-shadow .15s ease; }
  .cm-pin:hover, .cm-pin.on { transform: translate(-50%,-50%) scale(1.2); z-index: 6;
    box-shadow: 0 0 0 6px rgba(192,57,43,.18), 0 6px 16px rgba(0,0,0,.35); }
  .cm-card { position: absolute; right: 12px; top: 44px; z-index: 10; width: 292px;
    background: rgba(255,251,245,.98); border: 1px solid rgba(160,120,80,.38);
    border-radius: 14px; box-shadow: 0 18px 40px rgba(0,0,0,.22); overflow: hidden;
    transform: translateY(16px); opacity: 0; pointer-events: none; transition: all .18s ease; }
  .cm-card.open { transform: translateY(0); opacity: 1; pointer-events: auto; }
  .cm-x { position: absolute; right: 7px; top: 7px; z-index: 3; width: 24px; height: 24px; font-size: 14px; }
  .cm-photo { height: 118px; background-size: cover; background-position: center;
    background-color: #eadbc8; }
  .cm-photo.empty { display: none; }
  .cm-body { padding: 10px 12px 12px; }
  .cm-name { font-size: 16px; font-weight: 700; color: #3a2418; padding-right: 18px; }
  .cm-addr { font-size: 11px; color: #8a6a48; margin: 3px 0 6px; }
  .cm-intro { font-size: 12px; line-height: 1.65; color: #5b4636; }
  .cm-foot { position: absolute; left: 12px; right: 12px; bottom: 9px; z-index: 7;
    display: flex; justify-content: space-between; gap: 8px; font-size: 10.5px;
    color: #7a5a3a; text-shadow: 0 1px 0 rgba(255,255,255,.8); pointer-events: none; }
  .cm-foot span { opacity: .8; max-width: 62%; text-align: right; }
  @media (max-width: 720px) {
    .cm-card { width: calc(100% - 24px); }
    .cm-foot span { display: none; }
  }
</style>
<script>
(function () {
  const POIS = __DATA__;
  const wrap = document.getElementById('cm-wrap');
  const canvas = document.getElementById('cm-canvas');
  const stage = document.getElementById('cm-stage');
  const img = document.getElementById('cm-map');
  const pins = document.getElementById('cm-pins');
  const line = document.getElementById('cm-line');
  const card = document.getElementById('cm-card');
  const photo = document.getElementById('cm-photo');
  let k = 1, tx = 0, ty = 0, drag = null, selected = -1;

  // 编号点位
  pins.innerHTML = POIS.map((p, i) =>
    '<button class="cm-pin" data-i="' + i + '" style="left:' + p.x + '%;top:' + p.y + '%" title="' + esc(p.name) + '">' +
    p.i + '</button>').join('');
  line.setAttribute('points', POIS.map(p => (p.x * 10) + ',' + (p.y * 10)).join(' '));

  function apply() {
    stage.style.transform = 'translate(-50%,-50%) translate(' + tx + 'px,' + ty + 'px) scale(' + k + ')';
  }
  function fit() {
    const vw = canvas.clientWidth, vh = canvas.clientHeight;
    const r = img.naturalWidth / img.naturalHeight || 1;
    let w = vw, h = w / r;
    if (h > vh) { h = vh; w = h * r; }
    stage.style.width = w + 'px';
    stage.style.height = h + 'px';
    k = 1; tx = 0; ty = 0; apply();
  }
  img.addEventListener('load', fit);
  window.addEventListener('resize', fit);
  setTimeout(fit, 120);

  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  pins.addEventListener('click', ev => {
    const b = ev.target.closest('.cm-pin');
    if (!b) return;
    ev.stopPropagation();
    select(Number(b.dataset.i));
  });

  function select(i) {
    selected = i;
    const p = POIS[i];
    pins.querySelectorAll('.cm-pin').forEach((b, n) => b.classList.toggle('on', n === i));
    document.getElementById('cm-name').textContent = p.i + '. ' + p.name;
    document.getElementById('cm-addr').textContent = p.addr || '';
    document.getElementById('cm-intro').textContent = p.intro || '';
    if (p.img) {
      photo.classList.remove('empty');
      photo.style.backgroundImage = 'url("' + p.img + '")';
    } else {
      photo.classList.add('empty');
      photo.style.backgroundImage = 'none';
    }
    card.classList.add('open');
  }
  document.getElementById('cm-close').addEventListener('click', () => {
    card.classList.remove('open'); selected = -1;
    pins.querySelectorAll('.cm-pin').forEach(b => b.classList.remove('on'));
  });

  // 拖拽平移
  canvas.addEventListener('pointerdown', ev => {
    if (ev.target.closest('.cm-pin') || ev.target.closest('.cm-card')) return;
    drag = { x: ev.clientX, y: ev.clientY, tx: tx, ty: ty };
    canvas.style.cursor = 'grabbing';
    canvas.setPointerCapture(ev.pointerId);
  });
  canvas.addEventListener('pointermove', ev => {
    if (!drag) return;
    tx = drag.tx + (ev.clientX - drag.x);
    ty = drag.ty + (ev.clientY - drag.y);
    apply();
  });
  canvas.addEventListener('pointerup', ev => {
    drag = null; canvas.style.cursor = 'grab';
    try { canvas.releasePointerCapture(ev.pointerId); } catch (e) {}
  });
  canvas.addEventListener('wheel', ev => {
    ev.preventDefault();
    k = Math.max(0.8, Math.min(3.2, k * (ev.deltaY < 0 ? 1.12 : 0.9)));
    apply();
  }, { passive: false });

  document.getElementById('cm-in').addEventListener('click', () => {
    k = Math.min(3.2, k * 1.18); apply();
  });
  document.getElementById('cm-out').addEventListener('click', () => {
    k = Math.max(0.8, k / 1.18); apply();
  });
  document.getElementById('cm-reset').addEventListener('click', () => {
    k = 1; tx = 0; ty = 0; apply();
    card.classList.remove('open');
    pins.querySelectorAll('.cm-pin').forEach(b => b.classList.remove('on'));
  });
})();
</script>
"""
