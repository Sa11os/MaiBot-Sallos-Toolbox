"""在官方 Dashboard 上检查导航接缝、按钮命中范围与交互状态。"""

import asyncio
import logging
import shutil
import tempfile
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

from browser_smoke import ROOT, SPAHandler
from playwright.async_api import async_playwright

from sallos_toolbox.features.appearance.integration.controller import AppearanceIntegration


async def geometry(page, selector):
    return await page.locator(selector).first.evaluate(
        "e => { const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height,"
        "bottom:r.bottom,right:r.right,cy:r.y+r.height/2}; }"
    )


async def check_alignment(page, button_selector, height):
    header = await geometry(page, "[data-dashboard-header]")
    logo = await geometry(page, "[data-dashboard-logo-area]")
    button = await geometry(page, button_selector)
    assert abs(logo["bottom"] - header["bottom"]) <= 1, ("logo/header seam", logo, header)
    assert abs(button["cy"] - header["cy"]) <= 1, ("button center", button, header)
    assert button["width"] >= 44 and button["height"] >= 44, ("hit target", button)
    assert header["height"] == height, header
    title = await geometry(page, "[data-dashboard-logo-title]")
    assert title["right"] <= button["x"] - 4, ("logo/button spacing", title, button)
    # 圆角按钮内部靠近四边的位置都应命中同一按钮，避免被侧栏裁剪或相邻区域覆盖。
    for x, y in [(4, 22), (40, 22), (22, 4), (22, 40)]:
        hit = await page.evaluate(
            "([x,y,s]) => document.elementFromPoint(x,y)?.closest(s) !== null && "
            "document.elementFromPoint(x,y)?.closest(s) !== undefined",
            [button["x"] + x, button["y"] + y, button_selector],
        )
        assert hit, ("clipped button", button, x, y)
    return button


async def main():
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        dashboard = directory / "dashboard"
        shutil.copytree(ROOT / ".dev/dashboard/maibot_dashboard/dist", dashboard)
        integration = AppearanceIntegration(directory / "data", logging.getLogger("layout"), (dashboard, "1.9.9"))
        await integration.start()
        assert integration.status()["available"], integration.error
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SPAHandler, directory=str(dashboard)))
        Thread(target=server.serve_forever, daemon=True).start()
        output = ROOT / "test-results"
        output.mkdir(exist_ok=True)

        async def api(route):
            path = urlparse(route.request.url).path
            result = {"success": True}
            if path.endswith("/auth/check"):
                result.update(authenticated=True, requires_custom_token=False)
            elif path.endswith("/setup/status"):
                result.update(is_first_setup=False, requires_custom_token=False, token_source="custom")
            elif path.endswith("/runtime/webui"):
                result.update(schema_version=2, extensions=[], capabilities=[])
            await route.fulfill(json=result)

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(channel="msedge", headless=True)
                page = await browser.new_page(viewport={"width": 1440, "height": 900}, locale="zh-CN")
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                await page.route("**/api/**", api)
                await page.add_init_script(
                    "localStorage.setItem('maibot-theme-dashboard-style','modern');"
                    "localStorage.setItem('maibot-layout-sidebar-open','true');"
                )
                await page.goto(f"http://127.0.0.1:{server.server_port}/settings?tab=appearance")
                await page.wait_for_selector("[data-dashboard-sidebar]")
                mode = "[data-dashboard-sidebar] [data-dashboard-sidebar-mode-switch]"
                fix = "[data-dashboard-sidebar] [data-dashboard-sidebar-fix-switch]"
                try:
                    for side in ["left", "right"]:
                        for height, width in [(56, 224), (48, 160), (96, 360)]:
                            await integration.change(
                                "apply",
                                {
                                    "sidebar_side": side,
                                    "header_height": height,
                                    "sidebar_width": width,
                                    "font_size": 22 if width == 160 else 16,
                                },
                            )
                            await page.wait_for_function(
                                "([h,w]) => getComputedStyle(document.documentElement)"
                                ".getPropertyValue('--layout-header-height').trim() === h+'px' && "
                                "getComputedStyle(document.documentElement)"
                                ".getPropertyValue('--layout-sidebar-width').trim() === w+'px'",
                                arg=[height, width],
                            )
                            await page.wait_for_timeout(300)
                            await check_alignment(page, mode, height)
                            if height == 56:
                                await page.screenshot(path=str(output / f"navigation-{side}.png"))
                            await page.locator(mode).click()
                            await page.mouse.move(700, 500)
                            await page.wait_for_timeout(550)
                            await page.locator("[data-dashboard-sidebar-layout]").hover()
                            await page.locator(fix).wait_for()
                            await page.wait_for_timeout(350)
                            await check_alignment(page, fix, height)
                            await page.locator(fix).focus()
                            await page.keyboard.press("Enter")
                            await page.locator(mode).wait_for()
                            print("NAVIGATION_OK", side, height, width, flush=True)
                    await page.locator("[data-dashboard-topbar-collapse-key]:visible").click()
                    await page.wait_for_selector('[data-dashboard-header-collapsed="true"]')
                    await page.wait_for_timeout(250)
                    assert (await geometry(page, mode))["height"] == 44
                    await page.locator("[data-dashboard-topbar-toggle]:visible").first.click()
                    await page.wait_for_selector("[data-dashboard-header]:not([data-dashboard-header-collapsed])")
                    await page.wait_for_timeout(250)
                    await check_alignment(page, mode, 96)
                    # Desktop-only rules preserve narrow-screen navigation.
                    await page.set_viewport_size({"width": 390, "height": 844})
                    await page.wait_for_timeout(500)
                    assert not await page.locator("[data-dashboard-sidebar-layout]").is_visible()
                    assert await page.locator("html").evaluate("e => e.scrollWidth <= innerWidth + 1")
                    await integration.change("reset")
                    await page.wait_for_function("!document.documentElement.hasAttribute('data-plugin-appearance')")
                    await page.set_viewport_size({"width": 1440, "height": 900})
                    await page.wait_for_timeout(500)
                    assert (await geometry(page, "[data-dashboard-logo-area]"))["height"] == 42
                    assert not errors, errors
                    print("MOBILE_AND_RESTORE_OK", flush=True)
                except Exception:
                    await page.screenshot(path=str(output / "navigation-failure.png"))
                    raise
                finally:
                    await browser.close()
        finally:
            await integration.stop()
            server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
