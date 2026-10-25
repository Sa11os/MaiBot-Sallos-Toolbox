import importlib.util
import json
import logging
import shutil
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from maibot_sdk.components import collect_components
from pydantic import ValidationError

from sallos_toolbox.features.appearance.integration.controller import AppearanceIntegration
from sallos_toolbox.features.appearance.integration.installer import TAG, DashboardInstaller
from sallos_toolbox.features.appearance.models import AppearanceTheme
from sallos_toolbox.features.appearance.repository import PresetRepository

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / ".dev/dashboard/maibot_dashboard/dist"


class PresetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = PresetRepository(Path(self.temporary.name))

    def test_save_reload_update_delete(self):
        initial = self.repository.save(AppearanceTheme(name="  自定义  "), "", 0)
        identifier = initial.presets[0].id
        reloaded = PresetRepository(self.repository.path.parent)
        self.assertEqual(reloaded.read().presets[0].theme.name, "自定义")
        changed = reloaded.save(AppearanceTheme(sidebar_side="right"), identifier, 1)
        self.assertEqual(changed.revision, 2)
        self.assertEqual(len(changed.presets), 1)
        self.assertEqual(reloaded.delete(identifier, 2).presets, [])

    def test_concurrent_updates_preserve_first_write(self):
        def save():
            try:
                return self.repository.save(AppearanceTheme(), "", 0).revision
            except ValueError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: save(), range(2)))
        self.assertCountEqual(results, [1, "conflict"])
        self.assertEqual(len(self.repository.read().presets), 1)

    def test_corrupt_file_is_preserved(self):
        self.repository.path.write_text("broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.repository.save(AppearanceTheme(), "", 0)
        self.assertEqual(self.repository.path.read_text(), "broken")

    def test_reject_unsafe_or_invalid_theme(self):
        for theme in [
            {"font_size": 0},
            {"sidebar_width": "240"},
            {"extra": 1},
            {"name": "   "},
            {"regions": {"sidebar": "background-color:url(https://example.com)"}},
            {"regions": {"card": "position:fixed"}},
            {"primary": "red"},
        ]:
            with self.subTest(theme=theme), self.assertRaises(ValidationError):
                AppearanceTheme.model_validate(theme)

    def test_sdk_loader_and_api_registration(self):
        spec = importlib.util.spec_from_file_location(
            "toolbox_test", ROOT / "plugin.py", submodule_search_locations=[str(ROOT)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        components = collect_components(module.create_plugin())
        names = {component["name"] for component in components}
        self.assertTrue(
            {
                "appearance_catalog",
                "appearance_save",
                "appearance_delete",
                "appearance_apply",
                "appearance_preview",
                "appearance_reset",
            }.issubset(names)
        )

    def test_official_webui_schema(self):
        source = ROOT.parent / "MaiBot/src/plugin_runtime/webui_schema.py"
        if not source.exists():
            self.skipTest("Official host source required")
        spec = importlib.util.spec_from_file_location("official_webui_schema", source)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        extension = module.load_webui_extension(str(ROOT))
        self.assertEqual(extension.schema_version, 2)
        self.assertEqual(extension.pages[0].entry, "web/appearance.html")


@unittest.skipUnless(DASHBOARD.exists(), "Official Dashboard wheel required")
class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.dashboard = self.root / "dashboard"
        shutil.copytree(DASHBOARD, self.dashboard)
        self.original = (self.dashboard / "index.html").read_bytes()
        self.controller = AppearanceIntegration(
            self.root / "data", logging.getLogger("test"), (self.dashboard, "1.9.9")
        )
        self.addAsyncCleanup(self.controller.stop)

    async def test_apply_preview_reset_restore_and_reload(self):
        await self.controller.start()
        self.assertTrue(self.controller.status()["available"], self.controller.error)
        theme = AppearanceTheme(sidebar_side="right").model_dump()
        await self.controller.change("apply", theme)
        state = self.dashboard / "sallos-toolbox-appearance-v1/state.json"
        self.assertEqual(json.loads(state.read_bytes())["theme"]["sidebar_side"], "right")
        await self.controller.change("preview", AppearanceTheme(primary="#112233").model_dump())
        preview = json.loads(state.read_bytes())
        self.assertEqual(preview["fallback"], theme)
        self.assertGreater(preview["preview_seconds"], 18)
        await self.controller.stop()
        self.assertEqual((self.dashboard / "index.html").read_bytes(), self.original)
        self.assertIsNone(json.loads(state.read_bytes())["theme"])
        await self.controller.start()
        self.assertEqual(json.loads(state.read_bytes())["theme"], theme)
        await self.controller.change("reset")
        self.assertIsNone(json.loads(state.read_bytes())["theme"])

    async def test_unsupported_version_leaves_entry_intact(self):
        self.controller.target = (self.dashboard, "2.0.0")
        await self.controller.start()
        self.assertFalse(self.controller.status()["available"])
        self.assertEqual((self.dashboard / "index.html").read_bytes(), self.original)

    async def test_install_is_idempotent_and_restore_keeps_other_edits(self):
        await self.controller.start()
        installer = self.controller.installer
        installer.install(b"// test runtime")
        entry = self.dashboard / "index.html"
        self.assertEqual(entry.read_bytes().count(TAG), 1)
        entry.write_bytes(entry.read_bytes() + b"<!-- other change -->")
        await self.controller.stop()
        self.assertEqual(entry.read_bytes(), self.original + b"<!-- other change -->")
        self.assertEqual(len(list((self.root / "data/backups").glob("*.html"))), 1)

    async def test_read_only_entry_reports_failure_without_losing_original(self):
        from sallos_toolbox.features.appearance.integration.files import atomic_write

        def write(path, content):
            if path.name == "index.html":
                raise PermissionError("read-only filesystem")
            return atomic_write(path, content)

        with patch("sallos_toolbox.features.appearance.integration.installer.atomic_write", side_effect=write):
            await self.controller.start()
        self.assertIn("read-only", self.controller.error)
        self.assertEqual((self.dashboard / "index.html").read_bytes(), self.original)

    async def test_asset_collision_is_preserved(self):
        assets = self.dashboard / "sallos-toolbox-appearance-v1"
        assets.mkdir()
        (assets / "runtime.js").write_text("unrelated")
        installer = DashboardInstaller(self.dashboard, self.root / "backups", "1.9.9")
        with self.assertRaises(ValueError):
            installer.install(b"test")
        self.assertEqual((assets / "runtime.js").read_text(), "unrelated")

    async def test_host_upgrade_detected_before_apply(self):
        await self.controller.start()
        (self.dashboard / "index.html").write_bytes(self.original)
        with self.assertRaises(ValueError):
            await self.controller.change("apply", AppearanceTheme().model_dump())

    async def test_shared_dashboard_rejects_another_instance(self):
        await self.controller.start()
        other = DashboardInstaller(self.dashboard, self.root / "other-instance/backups", "1.9.9")
        with self.assertRaises(ValueError):
            other.install(b"// other instance")

    async def test_state_publish_failure_restores_entry(self):
        with patch.object(self.controller, "_publish", side_effect=PermissionError("state is read-only")):
            await self.controller.start()
        self.assertFalse(self.controller.status()["available"])
        self.assertEqual((self.dashboard / "index.html").read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
