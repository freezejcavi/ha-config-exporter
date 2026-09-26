from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from config import RepositoryConfig

DATA_DIR = Path("/data")
SSH_DIR = DATA_DIR / "ssh"
KEY_PATH = SSH_DIR / "id_ed25519"
KNOWN_HOSTS_PATH = SSH_DIR / "known_hosts"
WORK_DIR = DATA_DIR / "repository"


def run(
    *args: str,
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=check,
        text=True,
        capture_output=capture,
        env=merged_env,
    )


def ensure_ssh_material() -> bool:
    SSH_DIR.mkdir(parents=True, exist_ok=True)
    created = False

    if not KEY_PATH.exists():
        run(
            "ssh-keygen",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "ha-config-exporter@home-assistant",
            "-f",
            str(KEY_PATH),
        )
        created = True

    KEY_PATH.chmod(0o600)

    if not KNOWN_HOSTS_PATH.exists():
        with urllib.request.urlopen(
            "https://api.github.com/meta",
            timeout=20,
        ) as response:
            meta = json.load(response)

        ssh_keys = meta.get("ssh_keys") or []
        if not ssh_keys:
            raise RuntimeError("GitHub metadata did not return SSH host keys")

        KNOWN_HOSTS_PATH.write_text(
            "".join(f"github.com {key}\n" for key in ssh_keys),
            encoding="utf-8",
        )
        KNOWN_HOSTS_PATH.chmod(0o600)

    return created


def public_key() -> str:
    return KEY_PATH.with_suffix(".pub").read_text(encoding="utf-8").strip()


def git_env() -> dict[str, str]:
    command = (
        f"ssh -i {KEY_PATH} -o IdentitiesOnly=yes "
        f"-o UserKnownHostsFile={KNOWN_HOSTS_PATH} "
        "-o StrictHostKeyChecking=yes"
    )
    return {
        "GIT_SSH_COMMAND": command,
        "GIT_AUTHOR_NAME": "HA Config Exporter",
        "GIT_AUTHOR_EMAIL": "ha-config-exporter@home-assistant",
        "GIT_COMMITTER_NAME": "HA Config Exporter",
        "GIT_COMMITTER_EMAIL": "ha-config-exporter@home-assistant",
    }


def verify_remote_access(config: RepositoryConfig) -> None:
    result = run(
        "git",
        "ls-remote",
        "--heads",
        config.url,
        config.branch_name,
        check=False,
        env=git_env(),
    )
    if result.returncode != 0:
        raise PermissionError(
            "Cannot access target Git repository with the App deploy key.\n"
            "Add this public key to the target repository as a write-enabled Deploy Key:\n\n"
            f"{public_key()}\n\n"
            f"Git error: {result.stderr.strip()}"
        )


def prepare_repository(config: RepositoryConfig) -> tuple[Path, str]:
    verify_remote_access(config)

    if not (WORK_DIR / ".git").exists():
        if WORK_DIR.exists():
            shutil.rmtree(WORK_DIR)
        run(
            "git",
            "clone",
            "--branch",
            config.branch_name,
            "--single-branch",
            config.url,
            str(WORK_DIR),
            env=git_env(),
        )
    else:
        run("git", "remote", "set-url", "origin", config.url, cwd=WORK_DIR)
        run(
            "git",
            "fetch",
            "--prune",
            "origin",
            config.branch_name,
            cwd=WORK_DIR,
            env=git_env(),
        )
        run(
            "git",
            "reset",
            "--hard",
            f"origin/{config.branch_name}",
            cwd=WORK_DIR,
        )
        run("git", "clean", "-fd", cwd=WORK_DIR)

    expected_sha = run(
        "git",
        "rev-parse",
        f"origin/{config.branch_name}",
        cwd=WORK_DIR,
    ).stdout.strip()

    return WORK_DIR, expected_sha


def _tree_sha(commit_sha: str, repository: Path) -> str:
    return run(
        "git",
        "rev-parse",
        f"{commit_sha}^{{tree}}",
        cwd=repository,
    ).stdout.strip()


def _parent_count(commit_sha: str, repository: Path) -> int:
    content = run(
        "git",
        "cat-file",
        "-p",
        commit_sha,
        cwd=repository,
    ).stdout
    return sum(1 for line in content.splitlines() if line.startswith("parent "))


def publish_snapshot(
    repository: Path,
    *,
    config: RepositoryConfig,
    expected_remote_sha: str,
    dry_run: bool,
) -> dict[str, str | bool | int]:
    run("git", "add", "-A", cwd=repository)
    candidate_tree = run("git", "write-tree", cwd=repository).stdout.strip()
    remote_tree = _tree_sha(expected_remote_sha, repository)
    parents = _parent_count(expected_remote_sha, repository)

    if candidate_tree == remote_tree and parents == 0:
        return {
            "changed": False,
            "pushed": False,
            "normalized_history": False,
            "tree_sha": candidate_tree,
            "remote_sha": expected_remote_sha,
        }

    normalized_history = candidate_tree == remote_tree and parents > 0

    created = subprocess.run(
        ["git", "commit-tree", candidate_tree],
        cwd=repository,
        check=True,
        text=True,
        input=config.commit_message + "\n",
        capture_output=True,
        env={**os.environ, **git_env()},
    ).stdout.strip()

    if dry_run:
        return {
            "changed": True,
            "pushed": False,
            "normalized_history": normalized_history,
            "tree_sha": candidate_tree,
            "remote_sha": expected_remote_sha,
            "snapshot_sha": created,
        }

    ref = f"refs/heads/{config.branch_name}"
    run(
        "git",
        "push",
        f"--force-with-lease={ref}:{expected_remote_sha}",
        "origin",
        f"{created}:{ref}",
        cwd=repository,
        env=git_env(),
    )
    run("git", "reset", "--hard", created, cwd=repository)

    return {
        "changed": True,
        "pushed": True,
        "normalized_history": normalized_history,
        "tree_sha": candidate_tree,
        "remote_sha": expected_remote_sha,
        "snapshot_sha": created,
    }
