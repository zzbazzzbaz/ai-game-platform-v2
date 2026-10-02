#!/usr/bin/env python3
"""
M1 沙盒链路验证（腾讯云 AGS / E2B 兼容协议）

验收目标（对应规格 §13 M1）：
  1. 建立沙盒实例
  2. 在沙盒内后台运行 Node 游戏服务
  3. 沙盒内浏览器（Chromium）打开该服务
  4. 通过 CDP 从外部操作同一浏览器并截图
  5. 打印 NoVNC 预览地址，人工确认「可见画面、可操作」

用法：
  uv run --env-file .env m1_verify.py check
  uv run --env-file .env m1_verify.py run --keep
  uv run --env-file .env m1_verify.py kill <sandbox_id>
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
import time

try:
    from e2b import Sandbox
except ImportError:  # pragma: no cover
    sys.exit("缺少 e2b SDK，请先执行 `uv sync`")

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE / "assets"
ARTIFACTS = HERE / "artifacts"
WORKDIR = "/home/user/m1"
DEFAULT_PORT = 3000


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"环境变量 {name} 未设置（参考 .env.example）")
    return value


def _sandbox_id(sbx) -> str:
    return getattr(sbx, "sandbox_id", None) or getattr(sbx, "id", "<unknown>")


def _preview_urls(sbx) -> tuple[str, str]:
    token = sbx._envd_access_token
    host = sbx.get_host(9000)
    novnc = (
        f"https://{host}/novnc/vnc_lite.html"
        f"?access_token={token}&path=websockify%3Faccess_token%3D{token}"
    )
    cdp = f"https://{host}/cdp?access_token={token}"
    return novnc, cdp


def cmd_check(_args: argparse.Namespace) -> None:
    _require_env("E2B_API_KEY")
    domain = _require_env("E2B_DOMAIN")
    print(f"domain = {domain}")
    paginator = Sandbox.list()
    running = []
    while paginator.has_next:
        running.extend(paginator.next_items())
    print(f"运行中的沙盒数 = {len(running)}")
    for sbx in running:
        print("  -", _sandbox_id(sbx))
    print("预检通过：API Key / 域名有效。")


def cmd_run(args: argparse.Namespace) -> None:
    template = args.template or os.environ.get("AGS_TEMPLATE")
    if not template:
        sys.exit("缺少模板名：--template 或 AGS_TEMPLATE（控制台创建的沙盒工具名）")
    _require_env("E2B_API_KEY")
    _require_env("E2B_DOMAIN")
    port = args.port

    print(f"[1/6] 创建沙盒 template={template} timeout={args.timeout}s")
    sbx = Sandbox.create(template=template, timeout=args.timeout)
    sid = _sandbox_id(sbx)
    print(f"      sandbox_id = {sid}")

    ok = False
    try:
        print("[2/6] 上传占位游戏服务")
        sbx.commands.run(f"mkdir -p {WORKDIR}")
        sbx.files.write(f"{WORKDIR}/server.mjs", (ASSETS / "server.mjs").read_text())
        print("[3/6] 后台启动 Node 服务 :%d" % port)
        sbx.commands.run(
            f"cd {WORKDIR} && PORT={port} node server.mjs > server.log 2>&1",
            background=True,
        )

        up = False
        for _ in range(30):
            try:
                out = sbx.commands.run(
                    "curl -s -o /dev/null -w '%{http_code}' "
                    f"http://127.0.0.1:{port}/api/ping"
                ).stdout
            except Exception:
                out = None
            if (out or "").strip() == "200":
                up = True
                break
            time.sleep(1)
        if not up:
            print("      服务未就绪，server.log:")
            print(sbx.commands.run(f"cat {WORKDIR}/server.log 2>/dev/null").stdout)
            return
        print("      服务就绪 ✔")

        novnc, cdp = _preview_urls(sbx)

        print("[4/6] 通过 CDP 打开 http://127.0.0.1:%d 并截图" % port)
        from playwright.sync_api import sync_playwright

        ARTIFACTS.mkdir(exist_ok=True)
        shot = ARTIFACTS / "m1.png"
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(
                cdp, headers={"X-Access-Token": str(sbx._envd_access_token)}
            )
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(f"http://127.0.0.1:{port}", wait_until="load")
            page.wait_for_timeout(1500)
            print("      title =", page.title())
            page.screenshot(path=str(shot))
            browser.close()
        print("      screenshot =", shot)

        print("[5/6] 预览地址（浏览器打开，看到的应是同一个 Chromium 画面）")
        print("      NoVNC:", novnc)
        print("      CDP  :", cdp)
        print("[6/6] sandbox_id =", sid)
        ok = True
    finally:
        if args.keep:
            print(
                f"已保留沙盒（最长 {args.timeout}s）。"
                f"手动销毁：uv run --env-file .env m1_verify.py kill {sid}"
            )
        else:
            print("销毁沙盒 …")
            sbx.kill()
    print("M1 验证：", "通过" if ok else "未通过")


def cmd_kill(args: argparse.Namespace) -> None:
    _require_env("E2B_API_KEY")
    _require_env("E2B_DOMAIN")
    sbx = Sandbox.connect(args.sandbox_id)
    sbx.kill()
    print("killed", args.sandbox_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="M1 沙盒链路验证")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="仅校验 key/域名并列出运行中沙盒")
    p_check.set_defaults(func=cmd_check)

    p_run = sub.add_parser("run", help="完整 M1 验证")
    p_run.add_argument("--template", help="沙盒工具名，缺省读 AGS_TEMPLATE")
    p_run.add_argument("--timeout", type=int, default=1800, help="沙盒最长运行秒数")
    p_run.add_argument("--port", type=int, default=DEFAULT_PORT, help="占位服务端口")
    p_run.add_argument("--keep", action="store_true", help="验证后保留沙盒供人工查看")
    p_run.set_defaults(func=cmd_run)

    p_kill = sub.add_parser("kill", help="销毁指定沙盒")
    p_kill.add_argument("sandbox_id")
    p_kill.set_defaults(func=cmd_kill)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
