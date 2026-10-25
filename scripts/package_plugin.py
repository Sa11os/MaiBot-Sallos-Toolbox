"""构建可上传的标准插件 ZIP，使用固定时间戳保证可重复打包。"""

import hashlib
import json
import sys
import zipfile
from pathlib import Path

from build_config import default_config_toml
from build_webui import build

ROOT = Path(__file__).resolve().parents[1]


def package() -> Path:
    build(check=True)
    version = json.loads((ROOT / "_manifest.json").read_text(encoding="utf-8"))["version"]
    files = [
        ROOT / name
        for name in ["_manifest.json", "plugin.py", "webui.json", "LICENSE", "README.md", "web/appearance.html"]
    ]
    files += [
        file
        for file in (ROOT / "sallos_toolbox").rglob("*")
        if file.is_file() and file.suffix in {".py", ".js"} and "__pycache__" not in file.parts
    ]
    files += list((ROOT / "docs").glob("*.md"))
    destination = ROOT / "dist" / f"MaiBot-Sallos-Toolbox-{version}.zip"
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in sorted(files):
            info = zipfile.ZipInfo(file.relative_to(ROOT).as_posix(), (2026, 10, 25, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, file.read_bytes())
        info = zipfile.ZipInfo("config.toml", (2026, 10, 25, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        info.create_system = 3
        archive.writestr(info, default_config_toml().encode("utf-8"))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert "_manifest.json" in archive.namelist()
        assert "web/appearance.html" in archive.namelist()
        assert "config.toml" in archive.namelist()
        assert all(not name.startswith(("/", ".")) and ".." not in name.split("/") for name in archive.namelist())
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    print(f"Packaged {destination.name}: {destination.stat().st_size} bytes, SHA256 {digest}")
    return destination


if __name__ == "__main__":
    sys.exit(0 if package().exists() else 1)
