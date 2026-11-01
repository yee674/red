# -*- coding: utf-8 -*-
"""qa_intent 的回归测试（不依赖 Streamlit，直接 python test_qa_intent.py）。

覆盖四类意图 + 两条曾经踩过的坑：
  * 「水井图片」—— 「图片」这个词不能被当成实体名的一部分
  * 「一师水井」—— 不能被「一师」（湖南第一师范的别名）抢走，误判成两点关系
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_intent  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))


def build_index() -> dict:
    """建索引：直接复用 qa_intent.load_index，规则和 app.py 的 build_index 一致。"""
    return qa_intent.load_index(os.path.join(ROOT, "kg.json"))


CASES = [
    # (输入, 期望 intent, 期望实体, 期望字段)
    ("水井图片", "photo", "well", None),
    ("一师水井照片", "photo", "well", None),
    ("看看毛泽东", "photo", "mao", None),
    ("毛泽东入学年份", "fact", "mao", "入学年份"),
    ("毛泽东哪年入学", "fact", "mao", "入学年份"),
    ("毛泽东什么时候毕业", "fact", "mao", "毕业年份"),
    ("毛泽东在哪个班", "fact", "mao", "班级"),
    ("新民学会发生的年份", "fact", "xinmin", "成立年份"),
    ("新民学会时间", "fact", "xinmin", "成立时间"),
    ("猴子石缴枪哪一年", "fact", "houzishi", "发生年份"),
    ("工人夜学什么时候", "fact", "nightclass", "发生时间"),
    ("驱张运动年份", "fact", "quzhang", "发生年份"),
    ("毛泽东", "entity", "mao", None),
    ("一师水井", "entity", "well", None),
    ("冷水浴", "entity", None, None),
    ("毛泽东和杨昌济什么关系", "path", None, None),
    ("今天天气怎么样", "unknown", None, None),
]


def main() -> int:
    index = build_index()
    failed = 0
    for prompt, want_intent, want_entity, want_field in CASES:
        plan = qa_intent.detect(prompt, index, "zh")
        ok = plan.get("intent") == want_intent
        if ok and want_entity:
            ok = plan.get("entity") == want_entity
        if ok and want_field:
            ok = plan.get("field") == want_field
        if ok and want_intent == "path":
            ok = {plan.get("a"), plan.get("b")} == {"mao", "yangchangji"}
        flag = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"{flag}  {prompt:<16} → {plan}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} 通过")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
