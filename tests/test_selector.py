from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from config import ScopeConfig
from selector import (
    is_hard_denied,
    matches,
    matches_relative,
    sanitize_zigbee2mqtt_configuration,
    scan_for_secrets,
    should_copy,
    storage_default_allowed,
)


class SelectorTests(unittest.TestCase):
    def test_absolute_glob_matching(self) -> None:
        self.assertTrue(
            matches(
                "/homeassistant/.storage/core.entity_registry",
                ["/homeassistant/.storage/core.*registry"],
            )
        )

    def test_relative_glob_matching(self) -> None:
        self.assertTrue(
            matches_relative(
                "codex_tasks/abc/task.json",
                ["codex_tasks/*/task.json"],
            )
        )
        self.assertFalse(
            matches_relative(
                "codex_tasks/abc/output.json",
                ["codex_tasks/*/task.json"],
            )
        )

    def test_hard_security_deny(self) -> None:
        self.assertTrue(is_hard_denied("/homeassistant/secrets.yaml"))
        self.assertTrue(is_hard_denied("/homeassistant/.cloud/production_auth.json"))
        self.assertTrue(
            is_hard_denied("/addon_configs/a0d7b954_nodered/flows_cred.json")
        )
        self.assertTrue(
            is_hard_denied("/addon_configs/a0d7b954_nodered/flows_cred copy.json")
        )
        self.assertTrue(
            is_hard_denied("/homeassistant/.storage/core.config_entries")
        )
        self.assertFalse(
            is_hard_denied("/homeassistant/.storage/core.entity_registry")
        )

    def test_storage_default_policy(self) -> None:
        self.assertTrue(
            storage_default_allowed("/homeassistant/.storage/core.entity_registry")
        )
        self.assertTrue(
            storage_default_allowed("/homeassistant/.storage/core.future_registry")
        )
        self.assertTrue(
            storage_default_allowed("/homeassistant/.storage/lovelace.dashboard_home")
        )
        self.assertFalse(
            storage_default_allowed("/homeassistant/.storage/trace.saved_traces")
        )

    def test_builtin_codex_task_exception(self) -> None:
        source = Path("/nonexistent/task.json")
        self.assertTrue(
            should_copy(
                "/homeassistant/codex_tasks/abc/task.json",
                "codex_tasks/abc/task.json",
                source,
                scope_name="homeassistant",
                scope=ScopeConfig(),
            )
        )
        self.assertFalse(
            should_copy(
                "/homeassistant/codex_tasks/abc/output.json",
                "codex_tasks/abc/output.json",
                source,
                scope_name="homeassistant",
                scope=ScopeConfig(),
            )
        )

    def test_user_exclude_overrides_builtin_exception(self) -> None:
        source = Path("/nonexistent/task.json")
        self.assertFalse(
            should_copy(
                "/homeassistant/codex_tasks/abc/task.json",
                "codex_tasks/abc/task.json",
                source,
                scope_name="homeassistant",
                scope=ScopeConfig(exclude=("codex_tasks/**",)),
            )
        )

    def test_user_include_restores_ordinary_exclude(self) -> None:
        source = Path("/nonexistent/task.json")
        scope = ScopeConfig(
            exclude=("codex_tasks/**",),
            include=("codex_tasks/*/task.json",),
        )
        self.assertTrue(
            should_copy(
                "/homeassistant/codex_tasks/abc/task.json",
                "codex_tasks/abc/task.json",
                source,
                scope_name="homeassistant",
                scope=scope,
            )
        )

    def test_user_include_can_restore_safe_storage_file(self) -> None:
        source = Path("/nonexistent/trace.saved_traces")
        self.assertTrue(
            should_copy(
                "/homeassistant/.storage/trace.saved_traces",
                ".storage/trace.saved_traces",
                source,
                scope_name="homeassistant",
                scope=ScopeConfig(include=(".storage/trace.saved_traces",)),
            )
        )

    def test_hard_deny_cannot_be_restored_by_include(self) -> None:
        source = Path("/nonexistent/core.config_entries")
        self.assertFalse(
            should_copy(
                "/homeassistant/.storage/core.config_entries",
                ".storage/core.config_entries",
                source,
                scope_name="homeassistant",
                scope=ScopeConfig(include=(".storage/core.config_entries",)),
            )
        )

    def test_security_scan_allows_secret_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "homeassistant" / "configuration.yaml"
            target.parent.mkdir(parents=True)
            target.write_text("password: !secret mqtt_password\n", encoding="utf-8")
            scan_for_secrets(root)

    def test_security_scan_blocks_sensitive_json_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "addon_configs" / "example" / "config.json"
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps({"username": "user", "password": "secret-value"}),
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                scan_for_secrets(root)

    def test_node_red_flows_token_reference_is_not_treated_as_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "addon_configs" / "a0d7b954_nodered" / "flows.json"
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps(
                    [
                        {
                            "type": "e-mail",
                            "token": "oauth2Response.access_token",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            scan_for_secrets(root)

    def test_node_red_flows_still_blocks_high_confidence_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "addon_configs" / "a0d7b954_nodered" / "flows.json"
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps([{"value": "github_pat_REALLOOKINGTOKEN123"}]),
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                scan_for_secrets(root)

    def test_zigbee2mqtt_sanitizer_preserves_config_and_redacts_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "homeassistant" / "zigbee2mqtt" / "configuration.yaml"
            target.parent.mkdir(parents=True)
            target.write_text(
                "version: 4\n"
                "mqtt:\n"
                "  server: mqtt://core-mosquitto:1883\n"
                "  user: addons\n"
                "  password: real-password\n"
                "advanced:\n"
                "  channel: 25\n"
                "  network_key:\n"
                "    - 1\n"
                "    - 2\n"
                "  pan_id: 12345\n",
                encoding="utf-8",
            )

            sanitize_zigbee2mqtt_configuration(root)
            content = target.read_text(encoding="utf-8")

            self.assertIn('password: "<redacted>"', content)
            self.assertIn('network_key: "<redacted>"', content)
            self.assertNotIn("real-password", content)
            self.assertNotIn("    - 1", content)
            self.assertIn("  channel: 25", content)
            self.assertIn("  pan_id: 12345", content)


if __name__ == "__main__":
    unittest.main()
