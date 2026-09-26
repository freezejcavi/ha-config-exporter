from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from config import RepositoryConfig
from gitmirror import publish_snapshot


class GitMirrorTests(unittest.TestCase):
    def _git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            text=True,
            capture_output=True,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "test",
                "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "test",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
            },
        )
        return result.stdout.strip()

    def _root_repo(self, repo: Path) -> str:
        self._git(repo, "init", "-b", "main")
        (repo / "README.md").write_text("# mirror\n", encoding="utf-8")
        self._git(repo, "add", "README.md")
        self._git(repo, "commit", "-m", "initial")
        return self._git(repo, "rev-parse", "HEAD")

    def test_unchanged_parentless_snapshot_does_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            expected = self._root_repo(repo)
            result = publish_snapshot(
                repo,
                config=RepositoryConfig(url="git@github.com:test/test.git"),
                expected_remote_sha=expected,
                dry_run=True,
            )
            self.assertFalse(result["changed"])
            self.assertFalse(result["pushed"])
            self.assertEqual(result["changed_files"], [])

    def test_changed_tree_creates_parentless_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            expected = self._root_repo(repo)
            (repo / "homeassistant").mkdir()
            (repo / "homeassistant" / "configuration.yaml").write_text(
                "default_config:\n",
                encoding="utf-8",
            )

            result = publish_snapshot(
                repo,
                config=RepositoryConfig(url="git@github.com:test/test.git"),
                expected_remote_sha=expected,
                dry_run=True,
            )

            self.assertTrue(result["changed"])
            self.assertEqual(
                result["changed_files"],
                ["A\thomeassistant/configuration.yaml"],
            )
            snapshot = str(result["snapshot_sha"])
            content = self._git(repo, "cat-file", "-p", snapshot)
            self.assertFalse(any(line.startswith("parent ") for line in content.splitlines()))


if __name__ == "__main__":
    unittest.main()
