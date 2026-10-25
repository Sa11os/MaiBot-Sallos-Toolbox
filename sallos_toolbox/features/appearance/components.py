"""外观功能的静态 WebUI API。"""

from maibot_sdk import API

from .integration.controller import AppearanceIntegration
from .service import AppearanceService


class AppearanceComponents:
    appearance_service: AppearanceService
    appearance_integration: AppearanceIntegration

    def _appearance(self) -> AppearanceService:
        if not self.config.plugin.enabled or not self.config.appearance.enabled:
            raise ValueError("外观工作台已停用，请在插件配置中启用")
        return self.appearance_service

    @API("appearance_catalog", version="1", description="读取外观预设")
    async def appearance_catalog(self) -> dict:
        return {**await self._appearance().catalog(), "integration": self.appearance_integration.status()}

    @API("appearance_apply", version="1", description="应用服务器全站外观")
    async def appearance_apply(self, theme: dict) -> dict:
        self._appearance()
        return await self.appearance_integration.change("apply", theme)

    @API("appearance_preview", version="1", description="预览全站外观 20 秒")
    async def appearance_preview(self, theme: dict) -> dict:
        self._appearance()
        return await self.appearance_integration.change("preview", theme)

    @API("appearance_reset", version="1", description="恢复服务器原有外观")
    async def appearance_reset(self) -> dict:
        self._appearance()
        return await self.appearance_integration.change("reset")

    @API("appearance_save", version="1", description="保存外观预设")
    async def appearance_save(self, theme: dict, preset_id: str = "", revision: int = 0) -> dict:
        return await self._appearance().save(theme, preset_id, revision)

    @API("appearance_delete", version="1", description="删除个人外观预设")
    async def appearance_delete(self, preset_id: str, revision: int) -> dict:
        return await self._appearance().delete(preset_id, revision)
