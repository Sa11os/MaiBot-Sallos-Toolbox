"""从配置模型生成全新安装配置，输入仅为源码默认值。"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sallos_toolbox.config import ToolboxConfig  # noqa: E402


def default_config_toml() -> str:
    lines = ["# Generated from ToolboxConfig; fresh-install defaults only.", ""]

    def write_table(data: dict, path: tuple[str, ...] = ()) -> None:
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key) for key in data):
            raise ValueError("配置键需要使用 TOML 标识符")
        if path:
            lines.append(f"[{'.'.join(path)}]")
        for key, value in data.items():
            if isinstance(value, dict):
                continue
            if type(value) not in {str, bool, int, float}:
                raise ValueError(f"请为配置类型补充 TOML 序列化支持：{key}")
            lines.append(f"{key} = {json.dumps(value, ensure_ascii=False, allow_nan=False)}")
        lines.append("")
        for key, value in data.items():
            if isinstance(value, dict):
                write_table(value, (*path, key))

    write_table(ToolboxConfig().model_dump())
    return "\n".join(lines)
