"""将已提交版本发布到用户指定的公开仓库；凭据仅在进程内使用。"""

import json
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPO = "Sa11os/MaiBot-Sallos-Toolbox"


def publish():
    version = json.loads((ROOT / "_manifest.json").read_text(encoding="utf-8"))["version"]
    archive = ROOT / "dist" / f"MaiBot-Sallos-Toolbox-{version}.zip"
    if not archive.is_file():
        raise RuntimeError("请先构建插件 ZIP")
    credential = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        check=True,
    )
    fields = dict(line.split("=", 1) for line in credential.stdout.splitlines() if "=" in line)
    token = fields.get("password")
    if not token:
        raise RuntimeError("GitHub 凭据尚未配置")

    def request(url, method="GET", data=None, content_type="application/json"):
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": content_type,
        }
        payload = json.dumps(data).encode() if isinstance(data, dict) else data
        with urlopen(Request(url, data=payload, headers=headers, method=method), timeout=60) as response:
            return json.load(response)

    api = f"https://api.github.com/repos/{REPO}"
    try:
        release = request(f"{api}/releases/tags/v{version}")
    except HTTPError as exc:
        if exc.code != 404:
            raise
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        release = request(
            f"{api}/releases",
            "POST",
            {
                "tag_name": f"v{version}",
                "target_commitish": head,
                "name": f"Sallos 工具箱 {version}",
                "body": (ROOT / "docs/release-notes.md").read_text(encoding="utf-8"),
                "draft": True,
            },
        )
    existing = {asset["name"]: asset for asset in release.get("assets", [])}
    for file in [archive, archive.with_suffix(".zip.sha256")]:
        if file.name in existing:
            raise RuntimeError(f"发布附件已存在，请核对远端文件：{file.name}")
        url = release["upload_url"].split("{")[0] + "?name=" + quote(file.name)
        result = request(url, "POST", file.read_bytes(), "application/octet-stream")
        print(result["browser_download_url"])
    release = request(f"{api}/releases/{release['id']}", "PATCH", {"draft": False})
    print(release["html_url"])


if __name__ == "__main__":
    publish()
