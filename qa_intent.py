# -*- coding: utf-8 -*-
"""问答意图识别（纯标准库，不依赖 Streamlit，可以单独跑测试）。

一句话 → 五种意图之一：

    photo    看图     「一师水井图片」            → 只回一张图
    fact     查字段   「毛泽东入学年份」          → 只回该字段的值（不整卡）
    path     关系     「毛泽东和杨昌济什么关系」  → 交给 C 的 BFS 最短路
    entity   名片     「毛泽东」                  → 完整实体卡
    unknown  没认出来 → 给相近建议

三条设计原则（答辩可以直接讲）：

1. **先剥意图词，再匹配实体。** 「水井图片」整串拿去匹配是匹配不到的，
   先把「图片 / 照片 / 实拍」这类词剥掉，剩下的「水井」才是要查的实体。
2. **最长别名 + 区间不重叠。** 「一师水井」里同时含「一师」（湖南第一师范的别名），
   旧逻辑会把两处命中都当成实体，误判成「两点关系查询」。这里按「命中区间不能重叠、
   长的优先」筛选，一句话里剩下的才是真正被提到的实体。
3. **事实只从 facts 里取。** 问「入学年份」必须句中确实出现 kg.json 里登记的
   字段名或别名；查不到就退回完整名片，绝不靠模糊匹配去编一个数字。
"""
from __future__ import annotations

# 「想看图片」的说法。英文统一小写后比较，中英混输也认得。
PHOTO_WORDS = (
    "长什么样子", "长什么样", "什么样子", "有没有图片", "有没有照片", "有图吗",
    "图片", "照片", "配图", "实拍", "图像", "看看", "看一下", "看图",
    "show me a picture", "show me a photo", "picture", "photo", "image", "pic",
)


def load_index(kg_path: str) -> dict:
    """从 kg.json 建一份索引，规则和 app.py 的 build_index 完全一致。

    给 test_qa_intent.py / probe_intent.py 这类脚本用 —— 它们只想验证意图判断，
    没必要把 Streamlit 整套拖起来。
    """
    import json

    with open(kg_path, encoding="utf-8") as fh:
        kg = json.load(fh)
    nodes = {n["id"]: n for n in kg["nodes"]}
    aliases: dict[str, str] = {}
    for nid, node in nodes.items():
        for alias in [nid, node["name"], *node.get("aliases", [])]:
            alias = str(alias).strip()
            if alias:
                aliases.setdefault(alias, nid)
    return {"nodes": nodes, "aliases": aliases, "kg": kg}


# ============================================================
# 基础匹配
# ============================================================
def _strip_photo_words(text: str) -> str:
    """把「图片 / 照片 / 看看」这类意图词从句子中间挖掉，只留下实体名。"""
    out = text.lower()
    for word in sorted(PHOTO_WORDS, key=len, reverse=True):
        out = out.replace(word, " ")
    return out


def has_photo_intent(text: str) -> bool:
    low = (text or "").lower()
    return any(word in low for word in PHOTO_WORDS)


def match_entities(text: str, index: dict) -> list[str]:
    """按别名匹配实体，返回去重后的 id 列表（按在句中出现的先后）。

    关键：命中区间不允许重叠，长的优先 —— 这样「一师水井」只会留下「一师水井」，
    不会被「一师」抢先算成湖南第一师范。
    """
    low = (text or "").lower()
    if not low.strip():
        return []

    spans: list[tuple[int, int, str]] = []
    for alias, nid in index["aliases"].items():
        needle = str(alias).strip().lower()
        if not needle:
            continue
        start = low.find(needle)
        while start != -1:
            spans.append((start, start + len(needle), nid))
            start = low.find(needle, start + 1)

    # 长的先占位，短的与之重叠就丢弃
    spans.sort(key=lambda s: (-(s[1] - s[0]), s[0]))
    kept: list[tuple[int, int, str]] = []
    for start, end, nid in spans:
        if any(not (end <= ks or start >= ke) for ks, ke, _ in kept):
            continue
        kept.append((start, end, nid))

    kept.sort()
    out: list[str] = []
    for _, _, nid in kept:
        if nid not in out:
            out.append(nid)
    return out


# 通用疑问词 → 字段名里应当包含的关键词。
# 兜底用：句子里没有完整字段名「发生时间」，只说了「时间」时靠它接住。
# （年份系写在前面，句中同时出现「年份」「时间」时优先答年份。）
FIELD_HINTS = (
    ("哪一年", "年份"), ("哪年", "年份"), ("多少年", "年份"), ("几年", "年份"),
    ("年份", "年份"),
    ("什么时候", "时间"), ("什么时间", "时间"), ("具体时间", "时间"),
    ("日期", "时间"), ("何时", "时间"), ("时间", "时间"),
)


def find_fact(text: str, node: dict) -> dict | None:
    """在 node 的 facts 里找句中提到的字段。

    两级匹配：
      1. 精确匹配字段名 / 别名（最长命中优先）；
      2. 都没命中，再看有没有「年份 / 哪年 / 时间 / 什么时候」这类通用疑问词，
         有就找字段名里含对应关键词的那条。
    两级都落空才返回 None —— 宁可退回完整名片，也不瞎猜一个字段。
    """
    facts = node.get("facts") or []
    if not facts:
        return None
    low = (text or "").lower()

    best, best_len = None, 0
    for fact in facts:
        names = [fact.get("key", ""), fact.get("key_en", "")]
        names += list(fact.get("aliases") or [])
        names += list(fact.get("aliases_en") or [])
        for name in names:
            needle = str(name).strip().lower()
            if needle and needle in low and len(needle) > best_len:
                best, best_len = fact, len(needle)
    if best is not None:
        return best

    for hint, target in FIELD_HINTS:
        if hint in low:
            for fact in facts:
                if target in str(fact.get("key", "")):
                    return fact
    return None


# ============================================================
# 对外入口
# ============================================================
def detect(prompt: str, index: dict, lang: str = "zh") -> dict:
    """识别一句话的意图。返回 dict，至少含 intent 字段。

    photo   → {"entity": id}
    fact    → {"entity": id, "field": 字段名}
    path    → {"a": id, "b": id, "entities": [...]}
    entity  → {"entity": id}
    unknown → {}（调用方给相近建议）
    """
    text = (prompt or "").strip()
    if not text:
        return {"intent": "unknown"}

    photo = has_photo_intent(text)
    # 剥掉意图词再匹配；剥完匹配不到，就退回原文再试一次
    ids = match_entities(_strip_photo_words(text), index) if photo else []
    if not ids:
        ids = match_entities(text, index)
    if not ids:
        return {"intent": "unknown"}

    if photo:
        return {"intent": "photo", "entity": ids[0]}

    # 问到某个登记过的字段 → 只回字段值
    for nid in ids:
        fact = find_fact(text, index["nodes"][nid])
        if fact:
            return {"intent": "fact", "entity": nid, "field": fact.get("key", "")}

    if len(ids) >= 2:
        return {"intent": "path", "a": ids[0], "b": ids[1], "entities": ids}

    return {"intent": "entity", "entity": ids[0]}
