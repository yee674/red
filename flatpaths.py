# -*- coding: utf-8 -*-
"""资源定位：同时支持「子目录布局」和「平铺布局」。

平铺布局（方便一次性导入 GitHub，不用建子文件夹）：
    materials/mao.md        →  materials__mao.md
    assets/mao.jpg          →  assets__mao.jpg
    content/routes.json     →  content__routes.json
    static/leaflet.js       →  static__leaflet.js

查找顺序：子目录 → 前缀平铺 → 根目录同名文件。
"""
from __future__ import annotations

import os


def resolve(base: str, folder: str, name: str) -> str | None:
    """返回存在的文件路径，找不到返回 None。"""
    for cand in (os.path.join(base, folder, name),
                 os.path.join(base, f"{folder}__{name}"),
                 os.path.join(base, name)):
        if os.path.exists(cand):
            return cand
    return None


def resolve_any(base: str, folder: str, stem: str, exts) -> str | None:
    """带扩展名列表的解析：assets/<stem>.<ext>、assets__<stem>.<ext>、<stem>.<ext>。"""
    for ext in exts:
        hit = resolve(base, folder, f"{stem}{ext}")
        if hit:
            return hit
    return None


def list_folder(base: str, folder: str, exts) -> list[tuple[str, str]]:
    """列出某逻辑目录下的文件，返回 [(逻辑文件名, 真实路径)]。

    逻辑文件名 = 去掉目录/前缀后的名字，例如 "mao.md"、"mao.jpg"。
    """
    out: dict[str, str] = {}

    dir_path = os.path.join(base, folder)
    if os.path.isdir(dir_path):
        for name in sorted(os.listdir(dir_path)):
            path = os.path.join(dir_path, name)
            if os.path.isfile(path) and name.lower().endswith(tuple(exts)):
                out.setdefault(name, path)

    prefix = folder + "__"
    try:
        for name in sorted(os.listdir(base)):
            if not name.startswith(prefix):
                continue
            path = os.path.join(base, name)
            logical = name[len(prefix):]
            if os.path.isfile(path) and logical.lower().endswith(tuple(exts)):
                out.setdefault(logical, path)
    except OSError:
        pass

    return sorted(out.items())


def read_text(base: str, folder: str, name: str) -> str | None:
    path = resolve(base, folder, name)
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None
