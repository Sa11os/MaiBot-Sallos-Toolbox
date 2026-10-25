"""官方 Dashboard 静态包 + 本地真实插件服务；宿主 HTTP 接口使用测试替身。"""

import asyncio
import hashlib
import importlib.util
import json
import logging
import shutil
import sys
import tempfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sallos_toolbox.features.appearance.integration.controller import AppearanceIntegration  # noqa: E402
from sallos_toolbox.features.appearance.repository import PresetRepository  # noqa: E402
from sallos_toolbox.features.appearance.service import AppearanceService  # noqa: E402


class SPAHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if not Path(self.translate_path(self.path)).is_file():
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, *_):
        pass


def load_extension():
    source = ROOT.parent / "MaiBot/src/plugin_runtime/webui_schema.py"
    spec = importlib.util.spec_from_file_location("webui_schema_smoke", source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    extension = module.load_webui_extension(str(ROOT)).model_dump(mode="json")
    extension["plugin_id"] = "sallos.toolbox"
    extension["pages"][0]["document_revision"] = hashlib.sha256((ROOT / "web/appearance.html").read_bytes()).hexdigest()
    return extension


async def main():
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        dashboard = directory / "dashboard"
        shutil.copytree(ROOT / ".dev/dashboard/maibot_dashboard/dist", dashboard)
        integration = AppearanceIntegration(directory / "data", logging.getLogger("smoke"), (dashboard, "1.9.9"))
        await integration.start()
        assert integration.status()["available"], integration.error
        service = AppearanceService(PresetRepository(directory / "presets"))
        extension = load_extension()
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SPAHandler, directory=str(dashboard)))
        Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}"
        output = ROOT / "test-results"
        output.mkdir(exist_ok=True)
        errors = []
        unknown = set()

        async def api(route):
            path = urlparse(route.request.url).path
            body = route.request.post_data_json or {} if route.request.method == "POST" else {}
            result = {}
            try:
                if path.endswith("/auth/check"):
                    result = {"authenticated": True, "requires_custom_token": False}
                elif path.endswith("/setup/status"):
                    result = {"is_first_setup": False, "requires_custom_token": False, "token_source": "custom"}
                elif path == "/api/webui/plugins/runtime/webui":
                    result = {
                        "schema_version": 2,
                        "extensions": [extension],
                        "capabilities": ["custom_pages", "structured_arguments"],
                    }
                elif path.endswith("/appearance/document"):
                    result = {
                        "document": (ROOT / "web/appearance.html").read_text(encoding="utf-8"),
                        "revision": extension["pages"][0]["document_revision"],
                    }
                elif "/appearance/queries/catalog" in path:
                    result = {"result": {**await service.catalog(), "integration": integration.status()}}
                elif "/appearance/actions/" in path:
                    print("ACTION", path, flush=True)
                    name = path.rsplit("/", 1)[-1]
                    args = body.get("args", {})
                    if name in {"apply", "preview", "reset", "delete"}:
                        assert body.get("confirmed"), "host confirmation required"
                    if name == "save":
                        value = await service.save(**args)
                    elif name == "delete":
                        value = await service.delete(**args)
                    else:
                        value = await integration.change(name, args.get("theme"))
                    result = {"result": value}
                else:
                    unknown.add(path)
                await route.fulfill(json={"success": True, **result})
            except Exception as exc:
                await route.fulfill(status=400, json={"detail": str(exc)})

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(channel="msedge", headless=True)
                context = await browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
                await context.route("**/api/**", api)
                page = await context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                await page.goto(base + "/extensions/sallos.toolbox/appearance")
                frame = page.frame_locator('iframe[title="外观"]')
                try:
                    await frame.locator("#status").filter(has_text="工作台已就绪").wait_for(timeout=20000)
                    await page.wait_for_timeout(1000)
                    await page.screenshot(path=str(output / "desktop.png"), full_page=True)
                    print("EDITOR_READY", flush=True)
                    await frame.locator('[name="sidebar_side"]').select_option("right")
                    await frame.locator('[name="name"]').fill("浏览器验证预设")
                    await frame.locator("#save").click()
                    print(
                        "SAVE_BUTTON",
                        await frame.locator("#save").evaluate("e => ({handler:typeof e.onclick,disabled:e.disabled})"),
                        flush=True,
                    )
                    print("SAVE_STATUS", await frame.locator("#status").text_content(), flush=True)
                    await frame.locator("#status").filter(has_text="预设已保存").wait_for(state="attached")
                    await frame.locator("#apply").click()
                    print(
                        "CONFIRMATION", await page.locator('[role="alertdialog"], [role="dialog"]').all_text_contents()
                    )
                    await page.get_by_role("button", name="确认", exact=True).click()
                    await page.wait_for_selector('html[data-plugin-appearance="sallos.toolbox"]')
                    await page.screenshot(path=str(output / "applied.png"), full_page=True)
                    await page.goto(base + "/settings?tab=appearance")
                    await page.wait_for_selector("[data-dashboard-sidebar-layout]")
                    await page.wait_for_timeout(2500)
                    metrics = await page.locator("[data-dashboard-sidebar-layout]").evaluate(
                        "e => ({order:getComputedStyle(e).order,"
                        "width:e.getBoundingClientRect().width,x:e.getBoundingClientRect().x})"
                    )
                    print("SIDEBAR", json.dumps(metrics), flush=True)
                    assert metrics["order"] == "2" and metrics["x"] > 900, metrics
                    assert metrics["width"] in {64, 224}, metrics
                    sidebar_width = await page.locator("[data-dashboard-sidebar]").first.evaluate(
                        "e => e.getBoundingClientRect().width"
                    )
                    assert sidebar_width == 224, sidebar_width
                    header_height = await page.locator("[data-dashboard-header]").evaluate(
                        "e => e.getBoundingClientRect().height"
                    )
                    assert header_height == 56, header_height
                    await page.get_by_text("原版 Dashboard", exact=True).click()
                    await page.wait_for_function(
                        "document.querySelector('[data-dashboard-sidebar-layout]')"
                        ".getBoundingClientRect().width === 224"
                    )
                    await page.screenshot(path=str(output / "dashboard-global.png"), full_page=True)
                    await page.goto(base + "/extensions/sallos.toolbox/appearance")
                    await frame.locator("#status").filter(has_text="工作台已就绪").wait_for()
                    await page.set_viewport_size({"width": 390, "height": 844})
                    await page.wait_for_selector("html[data-plugin-appearance]")
                    await page.wait_for_timeout(1000)
                    await page.screenshot(path=str(output / "mobile.png"), full_page=True)
                    overflow = await frame.locator("body").evaluate("e => e.scrollWidth > innerWidth + 1")
                    assert not overflow, "mobile horizontal overflow"
                    # Stored server appearance survives navigation; preview returns to it automatically.
                    await integration.change("preview", {"primary": "#CC1122"})
                    await page.wait_for_function(
                        "getComputedStyle(document.documentElement).getPropertyValue('--color-primary').includes('354')"
                    )
                    await page.wait_for_timeout(21000)
                    await page.wait_for_function(
                        "getComputedStyle(document.documentElement).getPropertyValue('--color-primary').includes('210')"
                    )
                    # Per-tab emergency recovery also works with a server-applied theme.
                    await page.goto(base + "/settings?sallosAppearance=off")
                    await page.wait_for_timeout(2200)
                    assert await page.locator("html[data-plugin-appearance]").count() == 0
                    await page.goto(base + "/settings?sallosAppearance=on")
                    await page.wait_for_selector("html[data-plugin-appearance]")

                    async def offline(route):
                        await route.abort()

                    state_pattern = "**/sallos-toolbox-appearance-v1/state.json"
                    await page.route(state_pattern, offline)
                    await page.wait_for_function("!document.documentElement.hasAttribute('data-plugin-appearance')")
                    await page.wait_for_timeout(1500)
                    assert await page.locator("html[data-plugin-appearance]").count() == 0
                    await page.unroute(state_pattern, offline)
                    await page.wait_for_selector("html[data-plugin-appearance]")
                    # Simulate abrupt Runner loss: static files remain while lease renewals stop.
                    integration.task.cancel()
                    try:
                        await integration.task
                    except asyncio.CancelledError:
                        pass
                    await page.wait_for_function(
                        "!document.documentElement.hasAttribute('data-plugin-appearance')", timeout=35000
                    )
                    print("LEASE_EXPIRY_OK", flush=True)
                    await integration.start()
                    await page.wait_for_selector("html[data-plugin-appearance]")
                    await integration.stop()
                    await page.wait_for_function("!document.documentElement.hasAttribute('data-plugin-appearance')")
                    assert await page.locator("html").get_attribute("data-dashboard-style") == "modern"
                    print("RESTORE_OK", flush=True)
                except Exception:
                    if await page.locator('iframe[title="外观"]').count():
                        print("FRAME_STATUS", await frame.locator("#status").text_content(timeout=1000), flush=True)
                    await page.screenshot(path=str(output / "failure.png"), full_page=True)
                    print("BODY", (await page.locator("body").inner_text())[:3000], flush=True)
                    raise
                finally:
                    print("PAGE_ERRORS", json.dumps(errors, ensure_ascii=False), flush=True)
                    assert not errors, errors
                    print("UNMOCKED_API", json.dumps(sorted(unknown)), flush=True)
                    await browser.close()
        finally:
            await integration.stop()
            server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
