"""全站外观状态与租约；进程退出后浏览器自动回到宿主样式。"""

import asyncio
import json
import time
from pathlib import Path
from uuid import uuid4

from ..models import AppearanceTheme
from .discovery import discover_dashboard
from .files import atomic_write
from .installer import DashboardInstaller


class AppearanceIntegration:
    def __init__(self, data_dir: Path, logger, target: tuple[Path, str] | None = None):
        self.data_dir = data_dir
        self.logger = logger
        self.target = target
        self.installer: DashboardInstaller | None = None
        self.saved: dict | None = None
        self.preview: dict | None = None
        self.preview_until = 0.0
        self.task: asyncio.Task | None = None
        self.lock = asyncio.Lock()
        self.error = "接入尚未启动"

    def status(self) -> dict:
        return {
            "available": self.installer is not None and not self.error,
            "message": self.error or "全站接入已就绪，首次启用后请刷新整个 Dashboard",
            "dashboard_version": self.installer.version if self.installer else "",
            "active": self.saved is not None,
        }

    async def start(self) -> None:
        async with self.lock:
            if self.task and not self.task.done():
                return
            self.preview, self.preview_until = None, 0
            try:
                await asyncio.to_thread(self._install)
                self.error = ""
                self.task = asyncio.create_task(self._heartbeat())
            except Exception as exc:
                self.error = f"全站接入待处理：{exc}"
                self.logger.warning(self.error)
                if self.installer and self.installer.installed:
                    try:
                        await asyncio.to_thread(self.installer.restore)
                    except Exception as recovery:
                        self.logger.warning("入口恢复需要处理：%s", recovery)

    def _install(self) -> None:
        directory, version = self.target or discover_dashboard()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        state = self.data_dir / "active.json"
        if state.exists():
            if state.stat().st_size > 64_000:
                raise ValueError("已应用外观文件超过大小限制")
            raw = json.loads(state.read_text(encoding="utf-8"))
            self.saved = AppearanceTheme.model_validate(raw).model_dump() if raw else None
        self.installer = DashboardInstaller(directory, self.data_dir / "backups", version)
        runtime = Path(__file__).with_name("runtime.js").read_bytes()
        self.installer.install(runtime)
        self._publish()

    def _publish(self, enabled: bool = True) -> None:
        if self.installer is None:
            return
        remaining = max(0, self.preview_until - time.monotonic())
        payload = {
            "schema": 1,
            "lease": uuid4().hex,
            "ttl": 30,
            "theme": (self.preview if remaining else self.saved) if enabled else None,
            "fallback": self.saved if enabled else None,
            "preview_seconds": remaining if enabled else 0,
        }
        atomic_write(self.installer.assets / "state.json", json.dumps(payload, ensure_ascii=False).encode())

    async def _heartbeat(self) -> None:
        while True:
            await asyncio.sleep(8)
            async with self.lock:
                try:
                    if not await asyncio.to_thread(self.installer.intact):
                        raise ValueError("Dashboard 入口已更新，请重载插件以重新检测")
                    await asyncio.to_thread(self._publish)
                except Exception as exc:
                    self.error = f"全站接入暂停：{exc}"
                    self.logger.warning(self.error)
                    return

    async def change(self, operation: str, theme: dict | None = None) -> dict:
        validated = AppearanceTheme.model_validate(theme).model_dump() if operation in {"apply", "preview"} else None
        if operation not in {"apply", "preview", "reset"}:
            raise ValueError("未知外观操作")
        async with self.lock:
            if not self.status()["available"]:
                raise ValueError(self.error)
            if not await asyncio.to_thread(self.installer.intact):
                raise ValueError("Dashboard 入口已更新，请重载插件以重新检测")
            previous = (self.saved, self.preview, self.preview_until)
            try:
                if operation == "preview":
                    self.preview, self.preview_until = validated, time.monotonic() + 20
                else:
                    self.saved, self.preview, self.preview_until = validated, None, 0
                    await asyncio.to_thread(atomic_write, self.data_dir / "active.json", json.dumps(validated).encode())
                await asyncio.to_thread(self._publish)
            except Exception:
                self.saved, self.preview, self.preview_until = previous
                if operation != "preview":
                    await asyncio.to_thread(
                        atomic_write, self.data_dir / "active.json", json.dumps(self.saved).encode()
                    )
                raise
        return self.status()

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        async with self.lock:
            if self.installer and self.installer.installed:
                try:
                    await asyncio.to_thread(self._publish, False)
                finally:
                    await asyncio.to_thread(self.installer.restore)
            self.error = "全站接入已停用"
