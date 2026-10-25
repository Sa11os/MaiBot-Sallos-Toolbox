"""外观服务：校验调用并在线程中执行存储。"""

import asyncio

from .models import AppearanceTheme
from .presets import builtin_presets
from .repository import PresetRepository


class AppearanceService:
    def __init__(self, repository: PresetRepository):
        self.repository = repository

    async def catalog(self) -> dict:
        state = await asyncio.to_thread(self.repository.read)
        return {**state.model_dump(), "builtin": builtin_presets()}

    async def save(self, theme: dict, preset_id: str, revision: int) -> dict:
        validated = AppearanceTheme.model_validate(theme)
        state = await asyncio.to_thread(self.repository.save, validated, preset_id, revision)
        return state.model_dump()

    async def delete(self, preset_id: str, revision: int) -> dict:
        state = await asyncio.to_thread(self.repository.delete, preset_id, revision)
        return state.model_dump()
