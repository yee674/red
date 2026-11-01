# -*- coding: utf-8 -*-
"""意图探针：不改代码、不开页面，先看一句话会被判成什么。

用法（在源码目录里打开命令行）：
    python probe_intent.py 校训图片
    python probe_intent.py 毛泽东入学年份 一师水井 毛泽东和杨昌济什么关系

输出示例：
    校训图片
      intent = photo
      entity = school_motto（校训）
      有图?  assets/school_motto.jpg 存在

问句不对劲时先看这里：intent / entity 任何一个不对，再去改对应文件，
别一上来就改界面代码。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_intent  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")


def main() -> int:
    prompts = [p for p in sys.argv[1:] if p.strip()]
    if not prompts:
        print("用法：python probe_intent.py <问句> [问句…]")
        return 1

    index = qa_intent.load_index(os.path.join(ROOT, "kg.json"))
    for prompt in prompts:
        plan = qa_intent.detect(prompt, index, "zh")
        print(f"\n{prompt}")
        print(f"  intent = {plan.get('intent')}")
        nid = plan.get("entity")
        if nid:
            node = index["nodes"][nid]
            print(f"  entity = {nid}（{node.get('name', '')}）")
        if plan.get("field"):
            print(f"  field  = {plan['field']}")
        if plan.get("intent") == "path":
            print(f"  path   = {plan.get('a')} → {plan.get('b')}")

        # 图片通道：顺带看看配图在不在
        if plan.get("intent") == "photo" and nid:
            node = index["nodes"][nid]
            img = node.get("image") or f"{nid}.jpg"
            path = os.path.join(ASSETS, img)
            print(f"  有图?   {'是 → assets/' + img if os.path.exists(path) else '否 → 缺 assets/' + img}")
        if plan.get("intent") == "unknown":
            print("  没认出来：给 kg.json 里对应实体补别名，或给 PHOTO_WORDS 补说法")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
