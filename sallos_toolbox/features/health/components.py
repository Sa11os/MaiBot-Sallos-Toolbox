"""基础连通检查的 SDK 适配。"""

from typing import Any

from maibot_sdk import Command


class HealthComponents:
    @Command("sallos_toolbox_ping", description="检查工具箱：/sallos ping", pattern=r"^/sallos\s+ping\s*$")
    async def ping(self, stream_id: str = "", **kwargs: Any) -> tuple[bool, str, int]:
        if not self.config.plugin.enabled:
            return False, "Sallos 工具箱已停用", 0
        if not stream_id.strip():
            return False, "缺少聊天流 ID", 0
        reply = self.config.plugin.ping_reply
        if await self.ctx.send.text(reply, stream_id):
            return True, reply, 2
        return False, "连通检查回复发送失败", 0
