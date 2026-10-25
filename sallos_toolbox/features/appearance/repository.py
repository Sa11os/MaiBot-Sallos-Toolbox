"""外观数据的并发检查与原子写入。"""

import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from uuid import uuid4

from .models import AppearanceTheme, PresetState, SavedPreset


class PresetRepository:
    def __init__(self, directory: Path):
        self.path = directory / "presets.json"
        self._lock = RLock()

    def read(self) -> PresetState:
        with self._lock:
            if not self.path.exists():
                return PresetState()
            if self.path.stat().st_size > 512_000:
                raise ValueError("预设文件超过大小限制，请检查数据文件")
            return PresetState.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, theme: AppearanceTheme, preset_id: str, revision: int) -> PresetState:
        with self._lock:
            state = self._current(revision)
            if preset_id:
                index = next((i for i, preset in enumerate(state.presets) if preset.id == preset_id), None)
                if index is None:
                    raise ValueError("预设已删除，请刷新后重试")
                state.presets[index] = SavedPreset(id=preset_id, theme=theme)
            else:
                if len(state.presets) >= 50:
                    raise ValueError("已达到 50 个个人预设上限")
                state.presets.append(SavedPreset(id=uuid4().hex, theme=theme))
            return self._write(state)

    def delete(self, preset_id: str, revision: int) -> PresetState:
        with self._lock:
            state = self._current(revision)
            remaining = [preset for preset in state.presets if preset.id != preset_id]
            if len(remaining) == len(state.presets):
                raise ValueError("预设已删除，请刷新后重试")
            state.presets = remaining
            return self._write(state)

    def _current(self, revision: int) -> PresetState:
        state = self.read()
        if revision != state.revision:
            raise ValueError("预设已由其他页面更新，请刷新后重试")
        return state

    def _write(self, state: PresetState) -> PresetState:
        state.revision += 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix="presets-", suffix=".tmp", dir=self.path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(state.model_dump(), stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)
        return state
