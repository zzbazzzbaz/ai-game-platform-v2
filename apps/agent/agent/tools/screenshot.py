"""screenshot 工具：对沙盒内浏览器（NoVNC 显示的同一个 Chromium）截图自检。"""

from e2b import Sandbox
from langchain_core.tools import BaseTool
from langchain_core.tools import tool as make_tool

from agent.core.constants import NOVNC_PORT, SCREENSHOT_PATH, WORK_ROOT


def _cdp_url(sandbox: Sandbox) -> str:
    host = sandbox.get_host(NOVNC_PORT)
    token = sandbox._envd_access_token  # AGS 未暴露公开取址
    return f"https://{host}/cdp?access_token={token}"


def make_screenshot_tool(*, sandbox: Sandbox) -> BaseTool:
    """构造 screenshot 工具：CDP 截图保存到工作区 .runtime/（限次使用，禁止过度自测）。"""

    @make_tool
    def screenshot() -> str:
        """对沙盒内浏览器截图（保存到工作区 .runtime/screenshot.png），用于自检画面。"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return "截图失败：缺少 playwright 依赖"
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.connect_over_cdp(_cdp_url(sandbox))
                contexts = browser.contexts
                if contexts and contexts[0].pages:
                    page = contexts[0].pages[0]
                else:
                    page = browser.new_page()
                shot = page.screenshot()
                title = page.title()
                sandbox.files.write(SCREENSHOT_PATH, shot)
        except Exception as e:
            return f"截图失败：{e}"
        return f"已截图到 {SCREENSHOT_PATH}（当前页面标题：{title}；工作区：{WORK_ROOT}）"

    return screenshot
