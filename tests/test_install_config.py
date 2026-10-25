"""覆盖 ZIP 初次安装、宿主版本检查与启用开关先行的场景。"""

import ast
import logging
import sys
import tempfile
import tomllib
import unittest
import zipfile
from collections.abc import Mapping
from pathlib import Path
from unittest.mock import patch

from plugin import create_plugin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_config import default_config_toml  # noqa: E402
from package_plugin import package  # noqa: E402


def official_version_gate():
    """直接执行官方纯配置函数，隔离机器人网络、模型与数据库启动。"""
    source = ROOT.parent / "MaiBot/src/plugin_runtime/runner/runner_main.py"
    if not source.exists():
        raise unittest.SkipTest("Official host source required")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    names = {
        "PluginConfigVersionError",
        "_deep_copy_plugin_config_value",
        "_deep_copy_plugin_config_mapping",
        "_is_plugin_config_value_type_compatible",
        "_overlay_plugin_config_fields",
        "extract_plugin_config_version",
        "rebuild_plugin_config_data",
    }
    selected = [node for node in tree.body if getattr(node, "name", "") in names]
    runner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "PluginRunner")
    prepare = next(
        node for node in runner.body if getattr(node, "name", "") == "_prepare_plugin_config_for_version_update"
    )
    prepare.decorator_list = []
    selected.append(prepare)
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *selected],
        type_ignores=[],
    )
    namespace = {
        "Mapping": Mapping,
        "logger": logging.getLogger("host-version-test"),
        "compare_versions": lambda old, new: tuple(map(int, new.split("."))) > tuple(map(int, old.split("."))),
    }
    exec(compile(ast.fix_missing_locations(module), str(source), "exec"), namespace)
    return namespace["_prepare_plugin_config_for_version_update"]


class InstallConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = package()

    def test_archive_defaults_match_sdk_model(self):
        with zipfile.ZipFile(self.archive) as archive:
            raw = tomllib.loads(archive.read("config.toml").decode())
        plugin = create_plugin()
        self.assertEqual(raw, plugin.build_default_config())
        self.assertEqual(raw["plugin"]["config_version"], "1.1.0")
        prepared, _ = official_version_gate()(raw, plugin.build_default_config())
        plugin.set_plugin_config(prepared)
        self.assertTrue(plugin.config.appearance.enabled)

    def test_enable_switch_before_first_load_retains_version(self):
        raw = tomllib.loads(default_config_toml())
        for enabled in [False, True]:
            raw["plugin"]["enabled"] = enabled
            plugin = create_plugin()
            prepared, _ = official_version_gate()(raw, plugin.build_default_config())
            plugin.set_plugin_config(prepared)
            self.assertEqual(plugin.config.plugin.enabled, enabled)
            self.assertEqual(plugin.config.plugin.config_version, "1.1.0")

    def test_reported_config_reproduces_and_version_line_repairs(self):
        raw = tomllib.loads("[plugin]\nenabled = true\n")
        plugin = create_plugin()
        gate = official_version_gate()
        with self.assertRaises(ValueError):
            gate(raw, plugin.build_default_config())
        raw["plugin"]["config_version"] = "1.1.0"
        prepared, _ = gate(raw, plugin.build_default_config())
        plugin.set_plugin_config(prepared)
        self.assertTrue(plugin.config.plugin.enabled)
        self.assertTrue(plugin.config.appearance.enabled)

    def test_versioned_upgrade_preserves_user_values(self):
        raw = {"plugin": {"config_version": "1.0.0", "enabled": False, "ping_reply": "custom reply"}}
        plugin = create_plugin()
        prepared, persist = official_version_gate()(raw, plugin.build_default_config())
        self.assertTrue(persist)
        plugin.set_plugin_config(prepared)
        self.assertEqual(plugin.config.plugin.ping_reply, "custom reply")
        self.assertFalse(plugin.config.plugin.enabled)

    def test_packaging_uses_model_defaults_instead_of_runtime_file(self):
        import package_plugin

        # 模拟开发者目录中的私人配置，断言它保持原样且与安装包内容隔离。
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config.toml").write_text('[plugin]\nconfig_version="private-value"\n', encoding="utf-8")
            before = (root / "config.toml").read_bytes()
            for name in ["_manifest.json", "plugin.py", "webui.json", "LICENSE", "README.md", "web/appearance.html"]:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            with patch.object(package_plugin, "ROOT", root), patch.object(package_plugin, "build"):
                output = package()
            with zipfile.ZipFile(output) as archive:
                self.assertNotIn(b"private-value", archive.read("config.toml"))
            self.assertEqual((root / "config.toml").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
