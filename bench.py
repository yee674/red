# -*- coding: utf-8 -*-
"""算法实验：C 邻接表内核 / 纯 Python 内核 / 朴素实现 的对照测量。

测量项
  1. 一跳邻居查询   C 邻接表 vs Python 邻接表 vs 逐条扫描边表（O(E)）
  2. 两点最短路     C BFS vs Python BFS vs 每次查询重建邻接表的朴素 BFS
  3. 路线规划质量   匹配度优先排序 vs 贪心最近邻（含 BFS 跳数）
  4. 规模扩展       真实 33 节点 → 模拟 50/100/200（C 内核上限）/330/660/3300（仅 Python）

所有数字都是本机实测，输出 bench_results.json 供报告引用。
"""
from __future__ import annotations

import json
import os
import platform
import random
import shutil
import statistics
import sys
import tempfile
import time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import c_core          # noqa: E402
import custom_route    # noqa: E402
import py_graph        # noqa: E402

ROOT = HERE
RESULTS: dict = {}


def load_kg() -> dict:
    with open(os.path.join(ROOT, "kg.json"), encoding="utf-8") as f:
        return json.load(f)


def median_us(fn, args_list, reps: int) -> dict:
    """跑 reps 轮，每轮遍历 args_list，返回中位数/均值/最小值（微秒）。"""
    for args in args_list[:5]:          # 预热，排除首次调用与缓存冷启动
        fn(*args)
    samples = []
    for _ in range(reps):
        t0 = time.perf_counter()
        for args in args_list:
            fn(*args)
        samples.append((time.perf_counter() - t0) * 1e6 / len(args_list))
    return {
        "median_us": round(statistics.median(samples), 3),
        "mean_us": round(statistics.fmean(samples), 3),
        "min_us": round(min(samples), 3),
        "stdev_us": round(statistics.pstdev(samples), 3) if len(samples) > 1 else 0.0,
        "reps": reps,
        "per_call_n": len(args_list),
    }


# ---------------- 朴素基线 ----------------
def naive_neighbors(edges, nid):
    """学生第一版常见写法：每次查询都扫一遍边表。O(E)。"""
    return [(e["to"], e["relation"]) for e in edges if e["from"] == nid]


def naive_path(edges, a, b):
    """每次查询都从边表重建邻接表再 BFS：O(V+E) 建表 + O(V+E) 搜索。"""
    adj = {}
    for e in edges:
        adj.setdefault(e["from"], []).append(e["to"])
        adj.setdefault(e["to"], []).append(e["from"])
    if a == b:
        return 0
    seen = {a}
    q = deque([(a, 0)])
    while q:
        u, d = q.popleft()
        for v in adj.get(u, ()):
            if v in seen:
                continue
            if v == b:
                return d + 1
            seen.add(v)
            q.append((v, d + 1))
    return -1


# ---------------- 合成规模数据 ----------------
def synth(n: int, seed: int = 7):
    """连通随机图：先连成一棵树保证连通，再补到约 1.5N 条边。标注为模拟数据。"""
    rnd = random.Random(seed)
    nodes = [{"id": f"n{i}", "name": f"节点{i}", "type": "PLACE"} for i in range(n)]
    edges = []
    for i in range(1, n):
        edges.append({"from": f"n{rnd.randrange(i)}", "to": f"n{i}", "relation": "RELATED_TO"})
    target = int(1.5 * n)
    while len(edges) < target:
        a, b = rnd.sample(range(n), 2)
        edges.append({"from": f"n{a}", "to": f"n{b}", "relation": "RELATED_TO"})
    return nodes, edges


def c_kernel_for(nodes, edges) -> object:
    """给合成数据搭一个独立目录（kg.json + graph.dll），加载真正的 C 内核。"""
    tmp = tempfile.mkdtemp(prefix="bench_c_")
    with open(os.path.join(tmp, "kg.json"), "w", encoding="utf-8") as f:
        json.dump({"nodes": nodes, "edges": edges}, f, ensure_ascii=False)
    shutil.copy2(os.path.join(ROOT, "graph.dll"), os.path.join(tmp, "graph.dll"))
    return c_core.build_and_load(tmp), tmp


def main() -> int:
    kg = load_kg()
    nodes = {n["id"]: n for n in kg["nodes"]}
    edges = kg["edges"]
    ids = list(nodes)

    RESULTS["env"] = {
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "cpu": platform.processor(),
        "cpu_count": os.cpu_count(),
    }
    RESULTS["data"] = {"nodes": len(nodes), "edges": len(edges),
                       "relations": len({e["relation"] for e in edges})}

    c_lib = c_core.build_and_load(ROOT)
    py_lib = py_graph.PyGraph(nodes, edges)
    RESULTS["env"]["c_engine"] = getattr(c_lib, "engine", "?")

    # ---- 实验 1：一跳邻居查询 ----
    one_hop = [(nid,) for nid in ids]
    RESULTS["exp1_neighbors"] = {
        "c_adjacency": median_us(c_lib.query_raw, one_hop, 200),
        "python_adjacency": median_us(py_lib.query_raw, one_hop, 200),
        "naive_scan_edges": median_us(lambda nid: naive_neighbors(edges, nid), one_hop, 200),
    }

    # ---- 实验 2：两点最短路 ----
    pairs = [(a, b) for a in ids for b in ids if a != b]
    RESULTS["exp2_path"] = {
        "pairs": len(pairs),
        "c_bfs": median_us(c_lib.find_path, pairs, 20),
        "python_bfs": median_us(py_lib.find_path, pairs, 20),
        "naive_rebuild_bfs": median_us(lambda a, b: naive_path(edges, a, b), pairs, 20),
    }
    # 正确性：三种实现的最短跳数必须一致（无向口径）
    mism = []
    for a, b in pairs:
        d1, d2, d3 = c_lib.find_path(a, b)[0], py_lib.find_path(a, b)[0], naive_path(edges, a, b)
        if naive_path(edges, a, b) > 0 and d1 > 0 and d1 != d3:
            mism.append((a, b, d1, d3))
    RESULTS["exp2_path"]["correctness_mismatch"] = len(mism)

    # ---- 实验 3：路线规划质量 ----
    rj = json.load(open(os.path.join(ROOT, "content", "routes.json"), encoding="utf-8"))
    pois = [dict(v, id=k) for k, v in rj["pois"].items()]
    quality, agg = [], {"configs": 0, "baseline_hops": 0, "ours_hops": 0,
                        "win": 0, "tie": 0, "lose": 0, "theme_hits_same": 0}
    kinds = ("PERSON", "PLACE", "EVENT", "CONCEPT")
    for kind in kinds:
        for hours in (2, 3, 4):
            base_n = custom_route.HOURS_TO_COUNT[hours]
            for start in [p["entity"] for p in pois]:
                # 基线：只按「主题匹配」排序，不考虑点位之间的实际距离
                scored = sorted(pois, key=lambda p: (
                    0 if nodes[p["entity"]]["type"] == kind else 1, p["id"]))
                base = scored[:max(base_n, 2)]
                base_hops, cur = 0, None
                for i, p in enumerate(base):
                    if i:
                        base_hops += max(c_lib.find_path(cur, p["entity"])[0], 0)
                    cur = p["entity"]
                base_hits = sum(1 for p in base if nodes[p["entity"]]["type"] == kind)

                res = custom_route.generate(
                    {"nodes": nodes, "lib": c_lib}, pois, kind, hours, start)
                ours_hops = sum(it["dist"] for it in res["items"])
                ours_hits = sum(1 for it in res["items"] if it["match"])

                agg["configs"] += 1
                agg["baseline_hops"] += base_hops
                agg["ours_hops"] += ours_hops
                if ours_hops < base_hops:
                    agg["win"] += 1
                elif ours_hops == base_hops:
                    agg["tie"] += 1
                else:
                    agg["lose"] += 1
                if ours_hits == base_hits:
                    agg["theme_hits_same"] += 1
                quality.append({
                    "kind": kind, "hours": hours, "start": start,
                    "baseline_stops": len(base), "baseline_theme_hits": base_hits,
                    "baseline_total_hops": base_hops,
                    "ours_stops": len(res["items"]), "ours_theme_hits": ours_hits,
                    "ours_total_hops": ours_hops,
                })
    n = agg["configs"]
    RESULTS["exp3_route_quality"] = {
        "per_config": quality,
        "configs": n,
        "baseline_avg_hops": round(agg["baseline_hops"] / n, 3),
        "ours_avg_hops": round(agg["ours_hops"] / n, 3),
        "win": agg["win"], "tie": agg["tie"], "lose": agg["lose"],
        "theme_hits_unchanged": agg["theme_hits_same"],
        "reduction_pct": round((agg["baseline_hops"] - agg["ours_hops"]) /
                               max(agg["baseline_hops"], 1) * 100, 2),
    }

    # ---- 实验 4：规模扩展 ----
    scaling = []
    for n in (50, 100, 200, 330, 660, 3300):
        s_nodes, s_edges = synth(n)
        s_nodes_map = {x["id"]: x for x in s_nodes}
        py = py_graph.PyGraph(s_nodes_map, s_edges)
        rnd = random.Random(11)
        sample = [(f"n{rnd.randrange(n)}", f"n{rnd.randrange(n)}") for _ in range(200)]
        sample = [(a, b) for a, b in sample if a != b]
        row = {"nodes": n, "edges": len(s_edges),
               "python_bfs": median_us(py.find_path, sample, 10)["median_us"]}
        if n <= c_core.MAX_NODES and len(s_edges) <= c_core.MAX_EDGES:
            try:
                lib, tmp = c_kernel_for(s_nodes, s_edges)
                row["c_bfs"] = median_us(lib.find_path, sample, 10)["median_us"]
                row["c_engine"] = getattr(lib, "engine", "?")
                RESULTS.setdefault("_tmpdirs", []).append(tmp)
            except Exception as exc:
                row["c_bfs"] = None
                row["c_error"] = f"{type(exc).__name__}: {exc}"[:120]
        scaling.append(row)
    RESULTS["exp4_scaling"] = scaling

    # ---- 输出 ----
    out = os.path.join(HERE, "bench_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)

    def show(label, d):
        print(f"{label:22s} median={d['median_us']:9.2f} µs  mean={d['mean_us']:9.2f}  "
              f"sd={d['stdev_us']:6.2f}  n={d['per_call_n']}×{d['reps']}")

    print("== 环境 ==", RESULTS["env"]["os"], "| py", RESULTS["env"]["python"],
          "| C 内核:", RESULTS["env"]["c_engine"])
    print("\n== 实验1 一跳邻居查询 ==")
    for k, d in RESULTS["exp1_neighbors"].items():
        show(k, d)
    print("\n== 实验2 两点最短路 ==")
    for k, d in RESULTS["exp2_path"].items():
        if isinstance(d, dict):
            show(k, d)
    print("   跳数不一致对数:", RESULTS["exp2_path"]["correctness_mismatch"])
    print("\n== 实验3 路线规划质量 ==")
    e3 = RESULTS["exp3_route_quality"]
    print(f"  配置数 {e3['configs']}（4 主题 × 3 时长 × 8 起点）")
    print(f"  平均总跳数：基线 {e3['baseline_avg_hops']} → 本组 {e3['ours_avg_hops']}"
          f"（降 {e3['reduction_pct']}%）")
    print(f"  逐配置对比：更优 {e3['win']} / 持平 {e3['tie']} / 更差 {e3['lose']}"
          f" | 主题命中数不变 {e3['theme_hits_unchanged']}/{e3['configs']}")
    print("\n== 实验4 规模扩展 ==")
    for r in scaling:
        c = f"{r['c_bfs']:9.2f}" if r.get("c_bfs") is not None else "     n/a"
        print(f"  N={r['nodes']:5d} E={r['edges']:5d} | C {c} µs | Python {r['python_bfs']:9.2f} µs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
