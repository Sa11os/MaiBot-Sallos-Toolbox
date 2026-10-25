"""按官方 WebUI 选择规则定位资源，限定已经验证的版本。"""

import json
import os
from importlib import import_module, metadata
from pathlib import Path

SUPPORTED_VERSION = "1.9.9"


def discover_dashboard() -> tuple[Path, str]:
    if os.getenv("MAIBOT_WEBUI_USE_LOCAL_DASHBOARD", "").strip().lower() in {"1", "true", "yes", "on"}:
        root = import_module("src.common.paths").SOURCE_ROOT
        directory = root / "dashboard/dist"
        if (directory / "index.html").is_file():
            version = json.loads((root / "dashboard/package.json").read_text(encoding="utf-8"))["version"]
            return directory, version
    module = import_module("maibot_dashboard")
    return Path(module.get_dist_path()), metadata.version("maibot-dashboard")


def validate_dashboard(directory: Path, version: str) -> None:
    if version != SUPPORTED_VERSION:
        raise ValueError(f"当前 Dashboard {version}，此版本插件适配 Dashboard {SUPPORTED_VERSION}")
    if directory.is_symlink() or (directory / "index.html").is_symlink():
        raise ValueError("Dashboard 目录或入口为链接，请使用常规安装目录")
    entry = directory / "index.html"
    if not entry.is_file() or entry.stat().st_size > 1_000_000:
        raise ValueError("Dashboard 页面入口缺失或大小异常")
    if b"</head>" not in entry.read_bytes():
        raise ValueError("Dashboard 页面入口结构需要重新适配")
    required = {b"data-dashboard-sidebar-layout", b"data-dashboard-workspace-content", b"data-dashboard-header"}
    for file in (directory / "assets").glob("*.js"):
        if file.is_symlink() or file.stat().st_size > 20_000_000:
            continue
        content = file.read_bytes()
        required = {marker for marker in required if marker not in content}
        if not required:
            return
    raise ValueError("Dashboard 布局标记缺失，请更新适配版本")
