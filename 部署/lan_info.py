# -*- coding: utf-8 -*-
"""局域网部署信息：找出本机 IP、生成访问二维码与一个离线可开的入口页。

不联网也能跑：只用标准库 + 可选的 qrcode/Pillow。
"""
from __future__ import annotations

import base64
import io
import os
import re
import socket
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT = 8501


def primary_ip() -> str | None:
    """不产生真实流量地拿到默认出口网卡 IP（断网时也能用）。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None


def all_ips() -> list[str]:
    """尽量把本机所有可用的 IPv4 都找出来（含虚拟网卡），主网卡排最前。"""
    found: list[str] = []
    first = primary_ip()
    if first:
        found.append(first)

    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            found.append(ip)
    except OSError:
        pass

    # Windows：从 ipconfig 里再捞一遍（有些网卡 gethostbyname 拿不到）
    try:
        out = subprocess.run(["ipconfig"], capture_output=True, text=True,
                             encoding="mbcs", errors="ignore", timeout=8).stdout
        for line in out.splitlines():
            m = re.search(r"IPv4[^:：]*[:：]\s*([0-9.]+)", line)
            if m:
                found.append(m.group(1))
    except Exception:
        pass

    bad = ("127.", "169.254.", "0.", "255.")
    clean = []
    for ip in found:
        if not ip or ip.startswith(bad) or ip in clean:
            continue
        clean.append(ip)
    return clean


def make_qr(text: str) -> bytes | None:
    try:
        import qrcode
        img = qrcode.make(text)
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue()
    except Exception:
        return None


def main() -> None:
    ips = all_ips()
    if not ips:
        print("[!] 没找到本机 IP，请确认已连上 Wi-Fi/局域网。")
        return

    main_url = f"http://{ips[0]}:{PORT}"
    urls = [f"http://{ip}:{PORT}" for ip in ips]

    print("=" * 56)
    print("  红脉智谱 RedTrace AI · 局域网访问地址")
    print("=" * 56)
    for i, url in enumerate(urls):
        print(("  主地址： " if i == 0 else "  备用：   ") + url)
    print("-" * 56)
    print("  其他人需要和这台电脑连同一个 Wi-Fi / 局域网")
    print("  这台电脑保持“服务”窗口不要关，关掉服务就访问不了")
    print("  首次启动如果弹出防火墙提示，请点“允许访问”")
    print("=" * 56)

    qr = make_qr(main_url)
    if qr:
        try:
            with open(os.path.join(HERE, "访问二维码.png"), "wb") as f:
                f.write(qr)
            print("  二维码已生成：部署\\访问二维码.png（可投影或发给别人）")
        except OSError as exc:
            print(f"  [!] 二维码图片写不进去（{exc.__class__.__name__}），地址照上面用即可")
            print("      提示：如果目录是只读的，换个位置或去掉只读属性再试")

    # 离线入口页：本机双击即可打开，把地址和二维码展示给别人
    qr_tag = ""
    if qr:
        b64 = base64.b64encode(qr).decode()
        qr_tag = f'<img class="qr" src="data:image/png;base64,{b64}" alt="QR">'
    extra = "".join(f"<li><code>{u}</code></li>" for u in urls[1:])
    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>红脉智谱 · 访问入口</title>
<style>
 body{{margin:0;background:#14080a;color:#f5ebe6;font-family:"Microsoft YaHei",sans-serif;
      display:flex;align-items:center;justify-content:center;min-height:100vh}}
 .card{{max-width:720px;padding:36px 44px;border:1px solid rgba(232,192,125,.35);
        border-radius:24px;background:linear-gradient(140deg,rgba(126,28,24,.55),rgba(22,9,11,.75));
        box-shadow:0 24px 60px rgba(0,0,0,.5);text-align:center}}
 h1{{margin:.2em 0;font-size:30px}}
 .en{{color:#e8c07d;font-size:15px;letter-spacing:.08em;margin-bottom:18px}}
 .url{{font-size:30px;color:#ffe7c4;margin:14px 0 6px;word-break:break-all}}
 .qr{{width:240px;height:240px;border-radius:12px;background:#fff;padding:8px;margin:14px 0}}
 .tip{{color:#d7bdb6;font-size:14px;line-height:1.9;text-align:left}}
 ul{{color:#b9a49c;font-size:13px}}
 code{{color:#ffe7c4}}
</style></head><body>
 <div class="card">
   <h1>🚩 红脉智谱</h1>
   <div class="en">RedTrace AI · 一师红色文化知识图谱与智能研学平台</div>
   <div class="url">{main_url}</div>
   {qr_tag}
   <div class="tip">
     ✅ 手机/电脑连同一个 Wi-Fi，扫码或输入上面的地址即可使用<br>
     ✅ 不需要外网，本机断网也能访问<br>
     ✅ 这台电脑的「服务」窗口要一直开着，关掉就访问不了<br>
     ⚠️ 如果打不开：先点防火墙的「允许访问」，再确认手机和电脑在同一网段
   </div>
   <ul style="text-align:left">{"备用地址：" + extra if extra else ""}</ul>
 </div>
</body></html>"""
    try:
        with open(os.path.join(HERE, "访问入口.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print("  入口页已生成：部署\\访问入口.html（双击打开，可投影给其他人扫码）")
    except OSError as exc:
        print(f"  [!] 入口页写不进去（{exc.__class__.__name__}），直接用上面的地址即可")


if __name__ == "__main__":
    sys.exit(main())
