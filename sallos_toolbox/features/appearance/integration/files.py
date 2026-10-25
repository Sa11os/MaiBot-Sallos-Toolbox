"""保留权限的原子文件写入。"""

import os
import stat
import tempfile
from pathlib import Path


def atomic_write(path: Path, content: bytes) -> None:
    if path.is_symlink():
        raise ValueError("目标文件为链接，请检查 Dashboard 安装目录")
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    descriptor, name = tempfile.mkstemp(prefix=".sallos-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
