# -*- coding: utf-8 -*-
"""智能体的大模型规划层（可选）。

职责分工（这是本项目「智能体」的核心设计）：

    用户自然语言
        │
        ├─ agent_llm.plan()        大模型：理解需求 → 输出结构化 JSON（意图 + 参数）
        │       └─ validate()      参数白名单校验（实体必须存在、时长/主题必须合法）
        ├─ 工具层（确定性算法）      C 邻接表 BFS / 一跳邻居 / 贪心路线
        └─ 结果解释                 以工具返回值作为唯一事实来源

设计原则：
1. **可降级**：没有配置 API Key、网络失败、模型返回非法 JSON、参数校验不通过，
   一律返回 None，由 app.py 回退到规则引擎（别名最长匹配），页面不会白屏。
2. **参数先校验再执行**：模型只负责「说清楚要干什么」，不负责算。
   实体 id 必须存在于 kg.json，时长只能 2/3/4 小时，主题只能四种实体类型。
3. **可留痕**：每次调用都记一条日志（模型、耗时、是否重试、校验结果、工具名），
   供报告的「工具调用记录」和课程验收使用。

配置方式（二选一）：
    .streamlit/secrets.toml :  LLM_API_KEY = "sk-..."
                               LLM_BASE_URL = "https://api.deepseek.com/v1"
                               LLM_MODEL = "deepseek-chat"
    环境变量               :  LLM_API_KEY / LLM_BASE_URL / LLM_MODEL

兼容任何 OpenAI 风格的 /chat/completions 接口（DeepSeek、通义、智谱、Moonshot、
本地 vLLM / Ollama 的 OpenAI 兼容端口等），换 URL 和模型名即可。
"""
from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT = 30

VALID_INTENTS = ("path", "entity", "neighbors", "route", "unknown")
VALID_KINDS = ("PERSON", "PLACE", "EVENT", "CONCEPT")
VALID_HOURS = (2, 3, 4)

# 每次会话的调用记录（app.py 会把它们显示在「调用记录」里，并可导出 JSON）
CALL_LOG: list[dict] = []


# ============================================================
# 配置
# ============================================================
def _secret(name: str) -> str:
    """先读 Streamlit secrets，再读环境变量；都没有就返回空串。"""
    try:
        import streamlit as st

        value = st.secrets.get(name, "")
        if value:
            return str(value).strip()
    except Exception:
        pass
    return os.environ.get(name, "").strip()


def config() -> dict:
    return {
        "api_key": _secret("LLM_API_KEY"),
        "base_url": (_secret("LLM_BASE_URL") or DEFAULT_BASE).rstrip("/"),
        "model": _secret("LLM_MODEL") or DEFAULT_MODEL,
        "timeout": int(os.environ.get("LLM_TIMEOUT", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT),
    }


def available() -> bool:
    """只有配了 Key 才认为大模型可用；否则整个聊天页走规则引擎。"""
    return bool(config()["api_key"])


# ============================================================
# 提示词
# ============================================================
def _entity_table(index: dict) -> str:
    """把 33 个实体压成一张紧凑表给模型看（id、名称、类型、别名）。"""
    lines = []
    for nid, node in index["nodes"].items():
        aliases = "/".join(str(a) for a in node.get("aliases", [])[:4])
        lines.append(f"- id={nid} | 名称={node.get('name', '')} | 类型={node.get('type', '')}"
                     f" | 别名={aliases}")
    return "\n".join(lines)


def _messages(prompt: str, index: dict, lang: str) -> list[dict]:
    system = f"""你是「红脉智谱」红色文化知识图谱的智能体规划器。你唯一的任务是：
把用户的自然语言需求转成 JSON 参数，交给确定性算法工具执行。

可用工具：
1. path     —— 两点关系查询：用 C 语言邻接表 + BFS 求两实体间最短关系链
2. entity   —— 实体名片：查某实体的身份、一跳关系、两跳可达
3. route    —— 定制研学路线：按兴趣主题 + 时长，用贪心最近邻排一条路线

实体清单（只能使用这里的 id）：
{_entity_table(index)}

输出格式（只输出 JSON，不要解释、不要代码块）：
{{"intent": "path|entity|neighbors|route|unknown",
  "a": "起始实体id",
  "b": "目标实体id",
  "entity": "要查询的实体id",
  "kind": "PERSON|PLACE|EVENT|CONCEPT",
  "hours": 2,
  "reason": "一句话说明你的判断"}}

规则：
- 问两个实体的关系、怎么连起来、经由谁 → intent=path，a 与 b 都必填且不能相同
- 问一个实体是谁、有什么关系、周边 → intent=entity 或 neighbors，填 entity
- 要安排参观路线、几小时怎么逛、按兴趣推荐点位 → intent=route，
  填 kind（兴趣主题）、hours（2/3/4）和 start（起点实体 id）
- 提到的名字如果不在实体清单里 → intent=unknown，不要编造 id
- 用户语言：{"中文" if lang == "zh" else "英文"}，但 JSON 的字段值必须是上面的英文枚举和 id"""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]


# ============================================================
# HTTP 调用（只依赖标准库，避免云端多装依赖）
# ============================================================
def _post_chat(cfg: dict, messages: list[dict], json_mode: bool = True) -> str:
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0,
        "max_tokens": 400,
        "stream": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        f"{cfg['base_url']}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {cfg['api_key']}")

    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=cfg["timeout"]) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"] or ""


def _extract_json(text: str) -> dict | None:
    """模型偶尔会包一层 ```json，这里做一次容错剥离。"""
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


# ============================================================
# 参数校验（模型说了不算，这里说了才算）
# ============================================================
def validate(raw: dict | None, index: dict) -> tuple[dict | None, list[str]]:
    """把模型输出收敛成可执行参数；返回 (params, errors)。"""
    if not isinstance(raw, dict):
        return None, ["输出不是 JSON 对象"]

    nodes = index["nodes"]
    intent = str(raw.get("intent", "")).strip().lower()
    if intent not in VALID_INTENTS:
        return None, [f"intent 非法：{intent!r}"]
    if intent == "unknown":
        return {"intent": "unknown", "reason": str(raw.get("reason", ""))[:120]}, []

    params: dict = {"intent": intent, "reason": str(raw.get("reason", ""))[:120]}
    errors: list[str] = []

    def pick_id(*keys: str) -> str | None:
        for k in keys:
            v = str(raw.get(k, "") or "").strip()
            if v:
                return v
        return None

    if intent == "path":
        a, b = pick_id("a", "from", "entity"), pick_id("b", "to", "entity_b")
        if not a or not b:
            errors.append("path 需要同时给出 a 与 b")
        else:
            if a not in nodes:
                errors.append(f"起点 id 不在图谱中：{a}")
            if b not in nodes:
                errors.append(f"终点 id 不在图谱中：{b}")
            if a == b:
                errors.append("a 与 b 不能相同")
            params["a"], params["b"] = a, b

    elif intent in ("entity", "neighbors"):
        entity = pick_id("entity", "a", "id")
        if not entity:
            errors.append("entity 需要给出实体 id")
        elif entity not in nodes:
            errors.append(f"实体 id 不在图谱中：{entity}")
        else:
            params["entity"] = entity

    elif intent == "route":
        kind = str(raw.get("kind", "")).strip().upper()
        start = pick_id("start", "from", "a")
        hours = raw.get("hours")
        try:
            hours = int(hours)
        except (TypeError, ValueError):
            hours = None
        if kind not in VALID_KINDS:
            errors.append(f"kind 必须是 {'/'.join(VALID_KINDS)}，收到 {kind!r}")
        if hours not in VALID_HOURS:
            errors.append(f"hours 必须是 2/3/4，收到 {raw.get('hours')!r}")
        if not start:
            errors.append("route 需要给出起点 start")
        elif start not in nodes:
            errors.append(f"起点 id 不在图谱中：{start}")
        if not errors:
            params.update({"kind": kind, "hours": hours, "start": start})

    return (None, errors) if errors else (params, [])


# ============================================================
# 对外入口
# ============================================================
def plan(prompt: str, index: dict, lang: str = "zh") -> dict:
    """理解需求 → 结构化参数。返回 {'ok':bool, 'params':..., 'meta':{...}}。

    任何失败都不会抛异常给界面：ok=False 时由调用方回退规则引擎。
    """
    cfg = config()
    meta = {
        "engine": "llm",
        "model": cfg["model"],
        "attempts": 0,
        "elapsed_ms": 0.0,
        "repaired": False,
        "error": "",
        "validated": False,
    }
    started = time.perf_counter()

    if not cfg["api_key"]:
        meta["error"] = "未配置 LLM_API_KEY"
        meta["engine"] = "rule"
        return {"ok": False, "params": None, "meta": meta}

    messages = _messages(prompt, index, lang)
    last_raw, errors = None, ["未开始"]
    for attempt in (1, 2):
        meta["attempts"] = attempt
        try:
            # 第一次带 JSON 模式；个别兼容端点不支持 response_format，第二次去掉
            text = _post_chat(cfg, messages, json_mode=(attempt == 1))
        except urllib.error.HTTPError as exc:
            meta["error"] = f"HTTP {exc.code}"
            if attempt == 2:
                break
            continue
        except Exception as exc:  # 超时、DNS、TLS……
            meta["error"] = f"{type(exc).__name__}"
            break

        last_raw = _extract_json(text)
        params, errors = validate(last_raw, index)
        meta["elapsed_ms"] = (time.perf_counter() - started) * 1000
        if params is not None:
            meta["validated"] = True
            meta["repaired"] = attempt == 2
            return {"ok": True, "params": params, "meta": meta, "raw": last_raw}

        # 校验失败：把错误回喂给模型，让它自己修一次（这也是「参数校验」的证据）
        if attempt == 1:
            messages = messages + [
                {"role": "assistant", "content": json.dumps(last_raw or {}, ensure_ascii=False)},
                {"role": "user",
                 "content": "上面的 JSON 不合法：" + "；".join(errors) +
                            "。请只输出修正后的 JSON。"},
            ]

    meta["elapsed_ms"] = (time.perf_counter() - started) * 1000
    meta["error"] = meta["error"] or "；".join(errors)[:160]
    return {"ok": False, "params": None, "meta": meta, "raw": last_raw}


def log(entry: dict) -> None:
    """写一条调用记录（app.py 显示/导出用）。"""
    CALL_LOG.append(entry)
    if len(CALL_LOG) > 200:
        del CALL_LOG[:-200]


def clear_log() -> None:
    CALL_LOG.clear()
