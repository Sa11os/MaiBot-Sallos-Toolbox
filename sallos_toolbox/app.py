"""显式组合功能组件并装配运行期服务。"""

from typing import Any

from maibot_sdk import CONFIG_RELOAD_SCOPE_SELF, MaiBotPlugin

from .config import ToolboxConfig
from .features.appearance.components import AppearanceComponents
from .features.appearance.integration.controller import AppearanceIntegration
from .features.appearance.repository import PresetRepository
from .features.appearance.service import AppearanceService
from .features.health.components import HealthComponents


class SallosToolboxPlugin(HealthComponents, AppearanceComponents, MaiBotPlugin):
    config_model = ToolboxConfig

    async def on_load(self) -> None:
        self.appearance_service = AppearanceService(PresetRepository(self.ctx.paths.data_dir / "appearance"))
        self.appearance_integration = AppearanceIntegration(
            self.ctx.paths.data_dir / "appearance/integration", self.ctx.logger
        )
        if self.config.plugin.enabled and self.config.appearance.enabled:
            await self.appearance_integration.start()
        self.ctx.logger.info("Sallos 工具箱已加载：连通检查、外观工作台")

    async def on_unload(self) -> None:
        await self.appearance_integration.stop()
        self.ctx.logger.info("Sallos 工具箱已卸载")

    async def on_config_update(self, scope: str, config_data: dict[str, Any], version: str) -> None:
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            await self.appearance_integration.stop()
            if self.config.plugin.enabled and self.config.appearance.enabled:
                await self.appearance_integration.start()
            self.ctx.logger.info("Sallos 工具箱配置已更新：%s", version)
