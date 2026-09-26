from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


OPTIONS_PATH = Path("/data/options.json")


@dataclass(frozen=True)
class RepositoryConfig:
    url: str
    branch_name: str = "main"
    commit_message: str = "Home Assistant Config Snapshot"


@dataclass(frozen=True)
class ExportConfig:
    repository: RepositoryConfig
    include: tuple[str, ...] = field(default_factory=tuple)
    exclude: tuple[str, ...] = field(default_factory=tuple)
    dry_run: bool = False


def load_config(path: Path = OPTIONS_PATH) -> ExportConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    repo = raw.get("repository") or {}

    url = str(repo.get("url") or "").strip()
    if not url:
        raise ValueError("repository.url is required")

    if not (url.startswith("git@github.com:") or url.startswith("ssh://git@github.com/")):
        raise ValueError(
            "repository.url must use GitHub SSH, for example "
            "git@github.com:owner/repository.git"
        )

    branch = str(repo.get("branch_name") or "main").strip()
    if not branch:
        raise ValueError("repository.branch_name must not be empty")

    commit_message = str(
        repo.get("commit_message") or "Home Assistant Config Snapshot"
    ).strip()

    return ExportConfig(
        repository=RepositoryConfig(
            url=url,
            branch_name=branch,
            commit_message=commit_message,
        ),
        include=tuple(str(value).strip() for value in (raw.get("include") or []) if str(value).strip()),
        exclude=tuple(str(value).strip() for value in (raw.get("exclude") or []) if str(value).strip()),
        dry_run=bool(raw.get("dry_run", False)),
    )
