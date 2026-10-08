#!/usr/bin/env python3
"""M1b 验证：前端直接 iframe 嵌入 AGS NoVNC（不经过平台反代）

回答的问题：
  1. AGS 的 NoVNC 页面是否允许跨域 iframe 嵌入（X-Frame-Options / CSP frame-ancestors）；
  2. 本地页面 iframe 加载 NoVNC 后，画面（canvas）能否正常渲染（Playwright 截图）；
  3. WebSocket（websockify）直连是否成功。

用法：
  cd test/infra/sandbox
  uv run --env-file .env --with requests python m1b_novnc_iframe_verify.py
"""

import os
import pathlib
import subprocess
import sys
import time

import requests
from e2b import Sandbox
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

PORT = 8899


def main():
    sbx = Sandbox.create(template=os.environ["AGS_TEMPLATE"], timeout=900)
    sid = getattr(sbx, "sandbox_id", "?")
    print(f"[sandbox] {sid}")
    try:
        token = sbx._envd_access_token
        host = sbx.get_host(9000)
        novnc = (
            f"https://{host}/novnc/vnc.html"
            f"?access_token={token}&path=websockify%3Faccess_token%3D{token}"
            f"&autoconnect=1&resize=scale"
        )
        print(f"[novnc] {novnc}")

        r = requests.get(novnc, timeout=30)
        print(f"[headers] GET {r.status_code}")
        for h in ("X-Frame-Options", "Content-Security-Policy", "Server", "Content-Type"):
            print(f"  {h}: {r.headers.get(h)!r}")

        html = f"""<!doctype html><meta charset="utf-8"><title>embed test</title>
<body style="margin:0">
<iframe src="{novnc}" style="width:1280px;height:720px;border:0"
        allow="clipboard-read; clipboard-write"></iframe>
</body>"""
        page_file = ARTIFACTS / "m1b_embed.html"
        page_file.write_text(html)

        srv = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(PORT), "--directory", str(ARTIFACTS)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page(viewport={"width": 1300, "height": 760})
                page.goto(f"http://127.0.0.1:{PORT}/m1b_embed.html")
                page.wait_for_timeout(10000)
                shot = ARTIFACTS / "m1b_iframe.png"
                page.screenshot(path=str(shot))
                print(f"[screenshot] {shot}")

                print(f"[frames] {len(page.frames)}")
                for f in page.frames:
                    url = (f.url or "")[:90]
                    try:
                        canvases = f.locator("canvas").count()
                        title = f.evaluate("document.title")
                    except Exception:
                        canvases, title = "?", "?"
                    print(f"  url={url} title={title!r} canvas={canvases}")
                browser.close()
        finally:
            srv.terminate()
    finally:
        sbx.kill()
        print("[sandbox] killed")


if __name__ == "__main__":
    main()
