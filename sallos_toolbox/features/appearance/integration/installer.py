"""为原版 Dashboard 加载独立脚本，按标记恢复入口并保留第三方改动。"""

import hashlib
from pathlib import Path

from .discovery import validate_dashboard
from .files import atomic_write

ASSET_DIRECTORY = "sallos-toolbox-appearance-v1"
OWNER = b"sallos.toolbox appearance adapter v1\n"
TAG = (
    b"\n<!-- sallos.toolbox:appearance:v1 -->\n"
    b'<script defer src="/sallos-toolbox-appearance-v1/runtime.js"></script>\n'
    b"<!-- /sallos.toolbox:appearance:v1 -->\n"
)


class DashboardInstaller:
    def __init__(self, directory: Path, backup_directory: Path, version: str):
        self.directory = directory
        self.assets = directory / ASSET_DIRECTORY
        self.backups = backup_directory
        self.version = version
        self.installed = False
        self.owner = OWNER + hashlib.sha256(str(backup_directory.resolve()).encode()).hexdigest().encode()

    def install(self, runtime: bytes) -> None:
        validate_dashboard(self.directory, self.version)
        entry = self.directory / "index.html"
        original = entry.read_bytes()
        if original.count(TAG) > 1:
            raise ValueError("页面入口存在重复接入标记，请先恢复入口备份")
        if self.assets.is_symlink():
            raise ValueError("外观资源目录为链接，请检查目录")
        owner = self.assets / "owner.txt"
        if self.assets.exists() and (owner.is_symlink() or not owner.is_file() or owner.read_bytes() != self.owner):
            raise ValueError("外观资源路径已被其他实例或文件占用，请为各实例使用独立 Dashboard 安装目录")
        self.assets.mkdir(exist_ok=True)
        atomic_write(owner, self.owner)
        # 入口提交放在资源写入之后，写入失败时原页面仍可使用。
        atomic_write(self.assets / "runtime.js", runtime)
        if TAG not in original:
            self.backups.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(original).hexdigest()
            backup = self.backups / f"index-{digest}.html"
            if not backup.exists():
                atomic_write(backup, original)
            if entry.read_bytes() != original:
                raise ValueError("Dashboard 入口正在更新，请稍后重试")
            atomic_write(entry, original.replace(b"</head>", TAG + b"</head>", 1))
        self.installed = True

    def restore(self) -> None:
        entry = self.directory / "index.html"
        if entry.is_symlink():
            raise ValueError("页面入口已变为链接，请检查安装目录")
        original = entry.read_bytes()
        if TAG in original:
            atomic_write(entry, original.replace(TAG, b""))
        self.installed = False

    def intact(self) -> bool:
        entry = self.directory / "index.html"
        return entry.is_file() and not entry.is_symlink() and TAG in entry.read_bytes()
