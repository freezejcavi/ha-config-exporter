from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from config import load_config


class ConfigTests(unittest.TestCase):
    def _load(self, payload: dict[str, object]):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "options.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_config(path)

    def test_scoped_filters_are_relative(self) -> None:
        config = self._load(
            {
                "repository": {
                    "url": "git@github.com:test/repo.git",
                },
                "homeassistant": {
                    "exclude": ["codex_input/**"],
                    "include": ["codex_tasks/*/task.json"],
                },
                "addon_configs": {
                    "exclude": ["**/node_modules/**"],
                    "include": [],
                },
            }
        )
        self.assertEqual(config.homeassistant.exclude, ("codex_input/**",))
        self.assertEqual(config.homeassistant.include, ("codex_tasks/*/task.json",))
        self.assertEqual(config.addon_configs.exclude, ("**/node_modules/**",))

    def test_legacy_absolute_filters_are_mapped_by_root(self) -> None:
        config = self._load(
            {
                "repository": {
                    "url": "git@github.com:test/repo.git",
                },
                "include": [
                    "/homeassistant/codex_tasks/*/task.json",
                    "/addon_configs/example/config.json",
                ],
                "exclude": [
                    "/homeassistant/codex_input/**",
                    "/addon_configs/**/node_modules/**",
                ],
            }
        )
        self.assertEqual(
            config.homeassistant.include,
            ("codex_tasks/*/task.json",),
        )
        self.assertEqual(
            config.homeassistant.exclude,
            ("codex_input/**",),
        )
        self.assertEqual(
            config.addon_configs.include,
            ("example/config.json",),
        )
        self.assertEqual(
            config.addon_configs.exclude,
            ("**/node_modules/**",),
        )


if __name__ == "__main__":
    unittest.main()
