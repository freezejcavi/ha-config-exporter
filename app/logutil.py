from __future__ import annotations

import sys
from datetime import datetime

RESET = "\033[0m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
GREEN = "\033[32m"
MAGENTA = "\033[35m"
DIM = "\033[2m"

RUN_LINE = "#" * 72


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _emit(level: str, message: object, color: str, *, error_stream: bool = False) -> None:
    stream = sys.stderr if error_stream else sys.stdout
    lines = str(message).splitlines() or [""]
    stamp = timestamp()
    for line in lines:
        print(
            f"{color}[{stamp}] {level:<5} {line}{RESET}",
            file=stream,
            flush=True,
        )


def info(message: object) -> None:
    _emit("INFO", message, CYAN)


def warn(message: object) -> None:
    _emit("WARN", message, YELLOW)


def error(message: object) -> None:
    _emit("ERROR", message, RED, error_stream=True)


def ok(message: object) -> None:
    _emit("OK", message, GREEN)


def header(title: str) -> None:
    print(f"{MAGENTA}{RUN_LINE}{RESET}", flush=True)
    print(f"{MAGENTA}### {timestamp()} | {title}{RESET}", flush=True)
    print(f"{MAGENTA}{RUN_LINE}{RESET}", flush=True)


def footer(title: str, *, success: bool) -> None:
    color = GREEN if success else RED
    print(f"{color}{RUN_LINE}{RESET}", flush=True)
    print(f"{color}### {timestamp()} | {title}{RESET}", flush=True)
    print(f"{color}{RUN_LINE}{RESET}", flush=True)
