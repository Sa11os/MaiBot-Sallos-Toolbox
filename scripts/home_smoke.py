"""真实 Dashboard 首页响应式布局回归；使用合成统计与存储数据。"""

import asyncio
import importlib.util
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


def statistics_fixture():
    spec = importlib.util.spec_from_file_location(
        "stats_schema", ROOT.parent / "MaiBot/src/webui/schemas/statistics.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    points = [
        module.TimeSeriesData(
            timestamp=f"2026-10-25T{hour:02}:00:00",
            requests=hour * 3 + 10,
            input_tokens=hour * 2500 + 1000,
            output_tokens=hour * 800 + 100,
        )
        for hour in range(24)
    ]
    return module.DashboardData(
        summary=module.StatisticsSummary(
            total_requests=374,
            total_tokens=3190000,
            total_cost=22.15,
            avg_response_time=7.44,
            online_time=44640,
            total_messages=164,
            cache_hit_rate=0.1683,
            chat_cache_hit_rate=0.1059,
        ),
        hourly_data=points,
        daily_data=points,
        model_stats=[],
        recent_activity=[],
    ).model_dump()


async def main():
    stats = statistics_fixture()
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        dashboard = directory / "dashboard"
        shutil.copytree(ROOT / ".dev/dashboard/maibot_dashboard/dist", dashboard)
        integration = AppearanceIntegration(directory / "data", logging.getLogger("home"), (dashboard, "1.9.9"))
        await integration.start()
        await integration.change("apply", {"content_width": 720})
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
            elif path.endswith("/statistics/dashboard"):
                result = stats
            elif path.endswith("/system/status"):
                result.update(is_running=True, uptime=3600, version="1.3.15")
            elif path.endswith("/system/local-cache"):
                result.update(
                    directories=[
                        dict(key=k, total_size=s, file_count=50, db_records=20)
                        for k, s in [("images", 134000000), ("emoji", 95000000), ("logs", 838000000)]
                    ],
                    database=dict(total_size=77000000, files=[], tables=[]),
                )
            elif path.endswith("/news"):
                result.update(
                    items=[
                        dict(
                            id=str(i),
                            title="首页响应式布局验证",
                            summary="资讯内容在可用空间中自然排列。",
                            content="这是本地合成测试数据。",
                            published_at="2026-10-25T12:00:00",
                            url="https://example.com/news",
                            source="测试",
                            pinned=False,
                        )
                        for i in range(2)
                    ]
                )
            elif path.endswith("/runtime/home-cards"):
                result.update(cards=[])
            await route.fulfill(json=result)

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(channel="msedge", headless=True)
                page = await browser.new_page(viewport={"width": 2560, "height": 1032}, locale="zh-CN")
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                await page.route("**/api/**", api)
                await page.add_init_script("""
                  localStorage.setItem('maibot-theme-dashboard-style','modern');
                  localStorage.setItem('maibot-layout-sidebar-open','true');
                  localStorage.setItem('maibot-home-hitokoto-settings-v1',JSON.stringify({defaultEnabled:false,
                    customItems:[{id:'test',content:'让每一份信息都有舒适的位置，随窗口宽度自然排列。',source:'布局测试'}]}));
                """)
                try:
                    await page.goto(f"http://127.0.0.1:{server.server_port}/")
                    await page.wait_for_selector('[data-home-card-id="builtin:request-trend"] svg.recharts-surface')
                    await page.wait_for_function("document.documentElement.hasAttribute('data-plugin-appearance')")
                    for width, height in [
                        (2560, 1032),
                        (1920, 1080),
                        (1440, 900),
                        (1280, 720),
                        (900, 1000),
                        (390, 844),
                    ]:
                        await page.set_viewport_size({"width": width, "height": height})
                        await page.wait_for_timeout(600)
                        metrics = await page.evaluate("""() => {
                          const main=document.querySelector('[data-dashboard-main]');
                          const home=document.querySelector('[data-home-page]');
                          const cards=[...home.querySelectorAll('[data-home-card-id]')].map(e=>{
                            const r=e.getBoundingClientRect();
                            return {id:e.dataset.homeCardId,x:r.x,y:r.y,w:r.width,h:r.height};});
                          const hr=home.getBoundingClientRect();
                          return {width:hr.width, mainWidth:main.clientWidth,
                            scroll:main.scrollHeight-main.clientHeight,
                            overflow:document.documentElement.scrollWidth-innerWidth,cards,
                            innerScroll:[...main.querySelectorAll('[data-dashboard-scrollbar-viewport]')]
                              .filter(e=>e.querySelector('[data-home-page]')).map(e=>e.scrollHeight-e.clientHeight)};
                        }""")
                        print(
                            "HOME", width, height, "content", metrics["width"], "scroll", metrics["scroll"], flush=True
                        )
                        await page.screenshot(path=str(output / f"home-{width}.png"))
                        assert metrics["width"] >= metrics["mainWidth"] - 42, metrics
                        assert metrics["overflow"] <= 1, metrics
                        assert all(value <= 1 for value in metrics["innerScroll"]), metrics
                        cards = metrics["cards"]
                        assert len(cards) == 9, cards
                        for i, a in enumerate(cards):
                            assert a["w"] > 0 and a["h"] >= 40, a
                            for b in cards[i + 1 :]:
                                assert (
                                    a["x"] + a["w"] <= b["x"] + 1
                                    or b["x"] + b["w"] <= a["x"] + 1
                                    or a["y"] + a["h"] <= b["y"] + 1
                                    or b["y"] + b["h"] <= a["y"] + 1
                                ), (a, b)
                        if width >= 1920:
                            assert metrics["scroll"] <= 1, metrics
                        elif width >= 1280:
                            assert metrics["scroll"] <= 260, metrics
                        if width == 390:
                            assert len({round(c["x"]) for c in cards}) == 1, cards
                        storage = page.locator('[data-home-card-id="builtin:storage"]')
                        assert await storage.evaluate("""e=>{
                          const box=e.getBoundingClientRect();
                          const link=e.querySelector('[data-home-storage-action]').getBoundingClientRect();
                          return link.bottom<=box.bottom && link.right<=box.right;
                        }""")
                    await page.set_viewport_size({"width": 1920, "height": 1080})
                    await integration.change(
                        "apply",
                        {
                            "sidebar_side": "right",
                            "sidebar_width": 360,
                            "font_size": 22,
                            "header_height": 96,
                            "content_width": 720,
                        },
                    )
                    await page.wait_for_function("getComputedStyle(document.documentElement).fontSize==='22px'")
                    await page.wait_for_timeout(400)
                    assert await page.locator("[data-home-page]").evaluate("e=>e.scrollWidth<=e.clientWidth+1")
                    await page.screenshot(path=str(output / "home-large-type.png"))
                    saved_layout = await page.evaluate("localStorage.getItem('maibot-home-card-layout-v1')")
                    await page.get_by_role("button", name="编辑卡片", exact=True).click()
                    await page.wait_for_selector("[data-home-card-edit-overlay]")
                    assert (
                        await page.locator("[data-home-summary-cards]").evaluate(
                            "e=>getComputedStyle(e).gridTemplateColumns.split(' ').length"
                        )
                        == 10
                    )
                    await page.screenshot(path=str(output / "home-edit.png"))
                    assert await page.evaluate("localStorage.getItem('maibot-home-card-layout-v1')") == saved_layout
                    await page.goto(f"http://127.0.0.1:{server.server_port}/settings?tab=appearance")
                    await page.wait_for_selector("[data-dashboard-workspace-content]")
                    await page.wait_for_function("document.documentElement.hasAttribute('data-plugin-appearance')")
                    assert (
                        await page.locator("[data-dashboard-workspace-content]").evaluate(
                            "e=>getComputedStyle(e).maxWidth"
                        )
                        == "720px"
                    )
                    await integration.change("reset")
                    await page.wait_for_function("!document.documentElement.hasAttribute('data-plugin-appearance')")
                    assert not errors, errors
                    print("HOME_EDIT_AND_RESTORE_OK", flush=True)
                except Exception:
                    await page.screenshot(path=str(output / "home-failure.png"))
                    raise
                finally:
                    await browser.close()
        finally:
            await integration.stop()
            server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
