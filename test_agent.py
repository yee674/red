# -*- coding: utf-8 -*-
"""端到端测试大模型规划层：起一个假的 OpenAI 兼容服务，走真实的参数校验与工具分派。"""
import http.server
import json
import os
import sys
import threading

PORT = 8931
CALLS = []
SEEN = set()


def reply_for(prompt: str) -> dict:
    """按提示词内容返回不同规划，模拟真实模型的输出。"""
    if "路线" in prompt:
        return {"intent": "route", "kind": "PERSON", "hours": 3, "start": "mao",
                "reason": "按人物主题排 3 小时"}
    if "修一下" in prompt:
        # 第一次故意给一个不存在的实体，触发校验失败 + 重试修复
        if prompt not in SEEN:
            SEEN.add(prompt)
            return {"intent": "path", "a": "不存在的人", "b": "mao", "reason": "坏参数"}
        return {"intent": "path", "a": "yangchangji", "b": "heshuheng", "reason": "修正后"}
    if "谁" in prompt or "介绍" in prompt:
        return {"intent": "entity", "entity": "heshuheng", "reason": "查实体"}
    return {"intent": "path", "a": "yangchangji", "b": "heshuheng", "reason": "两点关系"}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        messages = body.get("messages", [])
        user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user = m.get("content", "")
                break
        CALLS.append({"json_mode": "response_format" in body, "user": user[:40]})
        plan = reply_for(user)
        payload = json.dumps({"choices": [{"message": {"content": "```json\n" +
                                                      json.dumps(plan, ensure_ascii=False) +
                                                      "\n```"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    os.environ["LLM_API_KEY"] = "test-key"
    os.environ["LLM_BASE_URL"] = "http://127.0.0.1:%d/v1" % PORT
    os.environ["LLM_MODEL"] = "mock-model"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=180)
    at.run()
    print("[boot] exceptions:", len(at.exception))

    cases = [
        ("杨昌济和何叔衡是怎么连起来的", "path"),
        ("何叔衡是谁，介绍一下", "entity"),
        ("按人物主题排一个3小时的路线，从毛泽东出发", "route"),
        ("修一下 杨昌济 到 何叔衡", "path-repair"),
    ]
    for prompt, expect in cases:
        at.chat_input[0].set_value(prompt).run()
        msg = at.session_state["messages"][-1]
        agent = msg.get("agent", {})
        print("\n[%s] %s" % (expect, prompt))
        print("   kind:", msg.get("kind"), "| engine:", agent.get("engine"),
              "| tool:", agent.get("tool"), "| validated:", agent.get("validated"),
              "| attempts:", agent.get("attempts"), "| repaired:", agent.get("repaired"),
              "| ms:", round(agent.get("elapsed_ms", 0), 1))
        print("   params:", json.dumps(agent.get("params", {}), ensure_ascii=False))
        if msg.get("kind") == "path":
            print("   hops:", msg.get("hops"), "| steps:", len(msg.get("steps", [])))
        if msg.get("kind") == "route":
            print("   route:", [(i["entity"], i["dist"]) for i in msg["items"]])
        if at.exception:
            print("   EXCEPTION:", [str(e.value)[:200] for e in at.exception])

    log = at.session_state.get("agent_log", [])
    print("\n[log] entries:", len(log))
    for e in log:
        print("   ", e["engine"], e["intent"], e["tool"], e["validated"],
              e["attempts"], e["repaired"], e["elapsed_ms"])

    del os.environ["LLM_API_KEY"]
    at2 = AppTest.from_file("app.py", default_timeout=180)
    at2.run()
    at2.chat_input[0].set_value("杨昌济和何叔衡是怎么连起来的").run()
    m2 = at2.session_state["messages"][-1]
    print("\n[no-key fallback] engine:", m2["agent"]["engine"], "| tool:", m2["agent"]["tool"],
          "| hops:", m2.get("hops"), "| exceptions:", len(at2.exception))

    print("\nmock calls:", len(CALLS), "| json_mode:", [c["json_mode"] for c in CALLS])
    server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
