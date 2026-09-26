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
class ScopeConfig:
    include: tuple[str, ...] = field(default_factory=tuple)
    exclude: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ExportConfig:
    repository: RepositoryConfig
    homeassistant: ScopeConfig = field(default_factory=ScopeConfig)
    addon_configs: ScopeConfig = field(default_factory=ScopeConfig)
    dry_run: bool = False


def _values(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(
        str(value).strip()
        for value in raw
        if str(value).strip()
    )


def _strip_legacy_root(pattern: str, root: str) -> str | None:
    value = pattern.strip().replace("\\", "/")
    prefix = f"/{root}/"
    if value == f"/{root}":
        return "**"
    if value.startswith(prefix):
        return value[len(prefix) :]
    return None


def _legacy_scope(raw: dict[str, object], root: str) -> ScopeConfig:
    include: list[str] = []
    exclude: list[str] = []

    for value in _values(raw.get("include")):
        relative = _strip_legacy_root(value, root)
        if relative is not None:
            include.append(relative)

    for value in _values(raw.get("exclude")):
        relative = _strip_legacy_root(value, root)
        if relative is not None:
            exclude.append(relative)

    return ScopeConfig(tuple(include), tuple(exclude))


def _scope(raw: object, *, fallback: ScopeConfig) -> ScopeConfig:
    if not isinstance(raw, dict):
        return fallback
    return ScopeConfig(
        include=_values(raw.get("include")),
        exclude=_values(raw.get("exclude")),
    )


def load_config(path: Path = OPTIONS_PATH) -> ExportConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    repo = raw.get("repository") or {}

    url = str(repo.get("url") or "").strip()
    if not url:
        raise ValueError("repository.url is required")

    if not url.startswith(("git@github.com:", "ssh://git@github.com/")):
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

    legacy_homeassistant = _legacy_scope(raw, "homeassistant")
    legacy_addon_configs = _legacy_scope(raw, "addon_configs")

    return ExportConfig(
        repository=RepositoryConfig(
            url=url,
            branch_name=branch,
            commit_message=commit_message,
        ),
        homeassistant=_scope(
            raw.get("homeassistant"),
            fallback=legacy_homeassistant,
        ),
        addon_configs=_scope(
            raw.get("addon_configs"),
            fallback=legacy_addon_configs,
        ),
        dry_run=bool(raw.get("dry_run", False)),
    )
