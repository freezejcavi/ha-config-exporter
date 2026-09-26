from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from supervisor import REDACTED, sanitize_option, write_app_metadata


class SupervisorMetadataTests(unittest.TestCase):
    def test_sanitize_option_uses_schema_and_nested_key_names(self) -> None:
        value = {
            "enabled": True,
            "password": "plain-secret",
            "nested": {
                "api_key": "abc123",
                "label": "keep-me",
            },
        }
        schema = {
            "password": "password",
            "nested": {
                "api_key": "str",
                "label": "str",
            },
        }

        result = sanitize_option(value, schema)

        self.assertEqual(result["enabled"], True)
        self.assertEqual(result["password"], REDACTED)
        self.assertEqual(result["nested"]["api_key"], REDACTED)
        self.assertEqual(result["nested"]["label"], "keep-me")

    def test_write_app_metadata_discovers_all_apps_and_repositories(self) -> None:
        responses = {
            "/addons": {
                "addons": [
                    {"slug": "z_future_app"},
                    {"slug": "a_existing_app"},
                ]
            },
            "/addons/a_existing_app/info": {
                "name": "Existing App",
                "slug": "a_existing_app",
                "version": "1.2.3",
                "state": "started",
                "boot": "auto",
                "auto_update": True,
                "watchdog": True,
                "protected": True,
                "options": {
                    "mode": "normal",
                    "password": "do-not-export",
                },
                "schema": {
                    "mode": "str",
                    "password": "password",
                },
            },
            "/addons/z_future_app/info": {
                "name": "Future App",
                "slug": "z_future_app",
                "version": "9.9.9",
                "state": "stopped",
                "boot": "manual",
                "auto_update": False,
                "watchdog": False,
                "protected": False,
                "options": {},
                "schema": {},
            },
            "/store/repositories": [
                {
                    "name": "Community",
                    "slug": "abcd1234",
                    "source": "https://github.com/example/apps",
                    "maintainer": "Ignored",
                },
                {"name": "Core", "slug": "core", "source": "core"},
                {"name": "Local", "slug": "local", "source": "local"},
            ],
        }

        def fake_get(path: str) -> object:
            return responses[path]

        with tempfile.TemporaryDirectory() as tmp, patch(
            "supervisor._api_get",
            side_effect=fake_get,
        ):
            root = Path(tmp)
            count = write_app_metadata(root)

            self.assertEqual(count, 3)
            app_dir = root / "derived" / "apps"
            self.assertTrue((app_dir / "a_existing_app.json").exists())
            self.assertTrue((app_dir / "z_future_app.json").exists())

            existing = json.loads(
                (app_dir / "a_existing_app.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(existing["version"], "1.2.3")
            self.assertEqual(existing["options"]["mode"], "normal")
            self.assertEqual(existing["options"]["password"], REDACTED)

            repositories = json.loads(
                (app_dir / "repositories.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                repositories,
                [
                    {
                        "name": "Community",
                        "slug": "abcd1234",
                        "source": "https://github.com/example/apps",
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
