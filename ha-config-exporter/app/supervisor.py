from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SUPERVISOR_BASE_URL = "http://supervisor"
SUPERVISOR_TOKEN_ENV = "SUPERVISOR_TOKEN"
REDACTED = "<redacted>"

SENSITIVE_KEY = re.compile(
    r"(?:^|[_-])(passwords?|passwd|tokens?|api[_-]?keys?|secrets?|"
    r"private[_-]?keys?|client[_-]?secrets?|credentials?|access[_-]?keys?|"
    r"refresh[_-]?tokens?)(?:$|[_-])",
    re.IGNORECASE,
)
SENSITIVE_VALUE = re.compile(
    r"(?:^|\b)(?:password|passwd|token|api[_-]?key|secret|private[_-]?key|"
    r"client[_-]?secret|credential|access[_-]?key|refresh[_-]?token)"
    r"\s*[:=]\s*\S+",
    re.IGNORECASE,
)


def _api_get(path: str) -> object:
    token = os.environ.get(SUPERVISOR_TOKEN_ENV, "").strip()
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN is unavailable")

    request = Request(
        f"{SUPERVISOR_BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as err:
        raise RuntimeError(
            f"Supervisor API {path} failed with HTTP {err.code}"
        ) from err
    except URLError as err:
        raise RuntimeError(
            f"Supervisor API {path} is unavailable: {err.reason}"
        ) from err
    except json.JSONDecodeError as err:
        raise RuntimeError(
            f"Supervisor API {path} returned invalid JSON"
        ) from err

    if isinstance(payload, dict) and "result" in payload:
        if payload.get("result") != "ok":
            message = payload.get("message") or payload.get("error") or "unknown error"
            raise RuntimeError(f"Supervisor API {path} failed: {message}")
        return payload.get("data")

    return payload


def _schema_is_password(schema: object) -> bool:
    return isinstance(schema, str) and "password" in schema.lower()


def _is_empty_value(value: object) -> bool:
    return value == "" or value == [] or value == {}


def _is_sensitive_key(key: object, value: object) -> bool:
    if isinstance(value, (bool, int, float)) or value is None or _is_empty_value(value):
        return False
    return bool(SENSITIVE_KEY.search(str(key)))


def _string_looks_sensitive(value: object) -> bool:
    return isinstance(value, str) and bool(SENSITIVE_VALUE.search(value))


def sanitize_option(value: object, schema: object = None, key: object = None) -> object:
    if _schema_is_password(schema):
        return REDACTED

    if key is not None and _is_sensitive_key(key, value):
        return REDACTED

    if isinstance(value, dict):
        schema_dict = schema if isinstance(schema, dict) else {}
        return {
            child_key: sanitize_option(
                child_value,
                schema_dict.get(child_key),
                child_key,
            )
            for child_key, child_value in value.items()
        }

    if isinstance(value, list):
        item_schema = schema[0] if isinstance(schema, list) and schema else None
        return [sanitize_option(item, item_schema) for item in value]

    if _string_looks_sensitive(value):
        return REDACTED

    return value


def _app_export(info: dict[str, object], slug: str) -> dict[str, object]:
    options = info.get("options")
    schema = info.get("schema")
    return {
        "auto_update": info.get("auto_update"),
        "boot": info.get("boot"),
        "name": info.get("name"),
        "options": sanitize_option(
            options if isinstance(options, dict) else {},
            schema,
        ),
        "protected": info.get("protected"),
        "slug": info.get("slug") or slug,
        "state": info.get("state"),
        "version": info.get("version"),
        "watchdog": info.get("watchdog"),
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_app_metadata(repository_root: Path) -> int:
    addons_payload = _api_get("/addons")
    if not isinstance(addons_payload, dict):
        raise TypeError(
            "Supervisor API /addons returned an unexpected payload"
        )

    raw_addons = addons_payload.get("addons")
    if not isinstance(raw_addons, list):
        raise TypeError(
            "Supervisor API /addons did not return an addons list"
        )

    slugs = sorted(
        {
            str(item.get("slug")).strip()
            for item in raw_addons
            if isinstance(item, dict)
            and str(item.get("slug") or "").strip()
        }
    )

    destination = repository_root / "derived" / "apps"
    files_written = 0

    for slug in slugs:
        info = _api_get(f"/addons/{slug}/info")
        if not isinstance(info, dict):
            raise TypeError(
                f"Supervisor API /addons/{slug}/info returned "
                "an unexpected payload"
            )
        _write_json(
            destination / f"{slug}.json",
            _app_export(info, slug),
        )
        files_written += 1

    repositories_payload = _api_get("/store/repositories")
    if not isinstance(repositories_payload, list):
        raise TypeError(
            "Supervisor API /store/repositories returned "
            "an unexpected payload"
        )

    repositories: list[dict[str, object]] = []
    for item in repositories_payload:
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        if source is None or source == "core" or source == "local":
            continue
        repositories.append(
            {
                "name": item.get("name"),
                "slug": item.get("slug"),
                "source": source,
            }
        )

    repositories.sort(
        key=lambda item: (
            str(item.get("name") or "").casefold(),
            str(item.get("slug") or ""),
        )
    )
    _write_json(destination / "repositories.json", repositories)
    return files_written + 1
