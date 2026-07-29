#!/usr/bin/env python3
"""Create and inspect local, expiring font context for an install batch."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCHEMA_VERSION = 1
DEFAULT_TTL_HOURS = 2.0
PLATFORMS = {"macos", "windows", "linux", "cross-platform"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("expires_at must be an ISO-8601 string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_context(path: Path) -> tuple[dict | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "font context file does not exist"
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"cannot read font context: {exc}"

    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        return None, "unsupported font context schema"
    languages = data.get("languages")
    platform = data.get("platform")
    if not isinstance(languages, list) or not languages or not all(
        isinstance(item, str) and item.strip() for item in languages
    ):
        return None, "font context languages must be a non-empty list"
    if platform not in PLATFORMS:
        return None, "font context platform is invalid"
    try:
        expires_at = _parse_timestamp(data.get("expires_at"))
    except ValueError as exc:
        return None, str(exc)
    if expires_at <= _now():
        return None, "font context has expired"
    return data, None


def set_context(path: Path, languages: list[str], platform: str, ttl_hours: float) -> dict:
    normalized = list(dict.fromkeys(item.strip() for item in languages if item.strip()))
    if not normalized:
        raise ValueError("at least one language is required")
    if platform not in PLATFORMS:
        raise ValueError("platform is invalid")
    if not 0 < ttl_hours <= 24:
        raise ValueError("ttl-hours must be greater than 0 and at most 24")

    created_at = _now()
    data = {
        "schema_version": SCHEMA_VERSION,
        "languages": normalized,
        "platform": platform,
        "created_at": _timestamp(created_at),
        "expires_at": _timestamp(created_at + timedelta(hours=ttl_hours)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    set_parser = subparsers.add_parser("set", help="write a local batch context")
    set_parser.add_argument("path", type=Path)
    set_parser.add_argument("--language", action="append", required=True, dest="languages")
    set_parser.add_argument("--platform", choices=sorted(PLATFORMS), required=True)
    set_parser.add_argument("--ttl-hours", type=float, default=DEFAULT_TTL_HOURS)

    show_parser = subparsers.add_parser("show", help="read an active batch context")
    show_parser.add_argument("path", type=Path)

    args = parser.parse_args()
    if args.command == "set":
        try:
            data = set_context(args.path, args.languages, args.platform, args.ttl_hours)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    data, error = load_context(args.path)
    if error:
        print(error)
        return 2
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
