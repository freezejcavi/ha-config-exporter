from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from components import write_component_index


class ComponentIndexTests(unittest.TestCase):
    def test_index_tracks_version_source_hash_and_export_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            repository = root / "repository"

            battery = source / "battery_health"
            battery.mkdir(parents=True)
            (battery / "manifest.json").write_text(
                json.dumps(
                    {
                        "domain": "battery_health",
                        "name": "Battery Health Analyzer",
                        "version": "0.1.0",
                        "documentation": (
                            "https://github.com/example/battery-health"
                        ),
                        "requirements": [],
                    }
                ),
                encoding="utf-8",
            )
            (battery / "sensor.py").write_text("VALUE = 1\n", encoding="utf-8")

            spook = source / "spook"
            nested = spook / "integrations" / "spook_inverse"
            nested.mkdir(parents=True)
            (spook / "manifest.json").write_text(
                json.dumps(
                    {
                        "domain": "spook",
                        "name": "Spook",
                        "version": "5.5.1",
                        "documentation": "https://spook.boo",
                        "issue_tracker": "https://github.com/frenck/spook/issues",
                        "requirements": ["cronsim==2.7"],
                    }
                ),
                encoding="utf-8",
            )
            (nested / "manifest.json").write_text(
                json.dumps(
                    {
                        "domain": "spook_inverse",
                        "name": "Inverse",
                        "version": "5.5.1",
                        "issue_tracker": "https://github.com/frenck/spook/issues",
                        "requirements": [],
                    }
                ),
                encoding="utf-8",
            )
            (spook / "repairs.py").write_text("VALUE = 2\n", encoding="utf-8")

            os.symlink(
                "/config/custom_components/spook/integrations/spook_inverse",
                source / "spook_inverse",
            )

            count = write_component_index(repository, source_root=source)
            self.assertEqual(count, 1)

            index = json.loads(
                (
                    repository
                    / "derived"
                    / "custom_components"
                    / "index.json"
                ).read_text(encoding="utf-8")
            )

            battery_record = index["components"]["battery_health"]
            self.assertEqual(battery_record["export_mode"], "full_source")
            self.assertEqual(battery_record["version"], "0.1.0")
            self.assertEqual(
                battery_record["source"],
                "https://github.com/example/battery-health",
            )
            self.assertEqual(len(battery_record["installed_tree_sha256"]), 64)

            spook_record = index["components"]["spook"]
            inverse_record = index["components"]["spook_inverse"]
            self.assertEqual(spook_record["export_mode"], "metadata_only")
            self.assertEqual(
                spook_record["source"],
                "https://github.com/frenck/spook",
            )
            self.assertEqual(
                inverse_record["installed_tree_sha256"],
                spook_record["installed_tree_sha256"],
            )
            self.assertEqual(
                index["links"]["spook_inverse"]["target"],
                "/config/custom_components/spook/integrations/spook_inverse",
            )

    def test_tree_hash_changes_when_installed_source_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            repository = root / "repository"
            component = source / "third_party"
            component.mkdir(parents=True)
            (component / "manifest.json").write_text(
                json.dumps(
                    {
                        "domain": "third_party",
                        "name": "Third Party",
                        "version": "1.0.0",
                    }
                ),
                encoding="utf-8",
            )
            code = component / "sensor.py"
            code.write_text("VALUE = 1\n", encoding="utf-8")

            write_component_index(repository, source_root=source)
            first = json.loads(
                (
                    repository
                    / "derived"
                    / "custom_components"
                    / "index.json"
                ).read_text(encoding="utf-8")
            )["components"]["third_party"]["installed_tree_sha256"]

            code.write_text("VALUE = 2\n", encoding="utf-8")
            write_component_index(repository, source_root=source)
            second = json.loads(
                (
                    repository
                    / "derived"
                    / "custom_components"
                    / "index.json"
                ).read_text(encoding="utf-8")
            )["components"]["third_party"]["installed_tree_sha256"]

            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
