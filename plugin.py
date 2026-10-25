"""Sallos 工具箱：MaiBot 插件入口。"""

from typing import Any

from maibot_sdk import CONFIG_RELOAD_SCOPE_SELF, Command, Field, MaiBotPlugin, PluginConfigBase


class PluginSettings(PluginConfigBase):
    """工具箱基础设置。"""

    __ui_label__ = "Sallos 工具箱"
    __ui_icon__ = "wrench"

    config_version: str = Field(default="1.0.0", description="配置结构版本")
    enabled: bool = Field(default=True, description="启用工具箱命令")
    ping_reply: str = Field(default="pong！Sallos 工具箱已就绪喵~", min_length=1, description="连通检查回复")


class ToolboxConfig(PluginConfigBase):
    """由 Runner 生成并维护 config.toml。"""

    plugin: PluginSettings = Field(default_factory=PluginSettings)


class SallosToolboxPlugin(MaiBotPlugin):
    """通过 SDK 能力代理与 MaiBot 交互。"""

    config_model = ToolboxConfig

    async def on_load(self) -> None:
        self.ctx.logger.info("Sallos 工具箱已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("Sallos 工具箱已卸载")

    async def on_config_update(self, scope: str, config_data: dict[str, Any], version: str) -> None:
        """Runner 在调用回调前更新配置实例，命令执行时读取最新值。"""
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            self.ctx.logger.info("Sallos 工具箱配置已更新：%s", version)

    @Command(
        "sallos_toolbox_ping",
        description="检查 Sallos 工具箱是否在线：/sallos ping",
        pattern=r"^/sallos\s+ping\s*$",
    )
    async def ping(self, stream_id: str = "", **kwargs: Any) -> tuple[bool, str, int]:
        """回复当前聊天，供首次安装和后续联调使用。"""
        if not self.config.plugin.enabled:
            return False, "Sallos 工具箱已停用", 0
        if not stream_id.strip():
            return False, "缺少聊天流 ID", 0

        reply = self.config.plugin.ping_reply
        sent = await self.ctx.send.text(reply, stream_id)
        if sent:
            return True, reply, 2
        return False, "连通检查回复发送失败", 0


def create_plugin() -> SallosToolboxPlugin:
    """MaiBot Runner 调用的插件工厂。"""
    return SallosToolboxPlugin()
