#!/usr/bin/env python3
"""Validate a public release tree for structure and accidental private data."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


REQUIRED = {
    Path("README.md"),
    Path("LICENSE"),
    Path("SECURITY.md"),
    Path("skill-install-auditor/SKILL.md"),
    Path("skill-install-auditor/scripts/audit_skill.py"),
    Path("skill-install-auditor/scripts/manage_batch.py"),
}
SKIP_CONTENT_CHECK = {
    Path("tools/check_release.py"),
    Path("skill-install-auditor/scripts/audit_skill.py"),
    Path("skill-install-auditor/tests/test_audit_skill.py"),
}
TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
PRIVATE_PATTERNS = {
    "macOS user path": re.compile(r"/Users/[^/\s\"']+/"),
    "external volume path": re.compile(r"/Volumes/[^/\s\"']+/"),
    "Windows user path": re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\\\s\"']+\\\\"),
    "migration artifact": re.compile(r"\bMigration[_-]\d{4}"),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgh[ps]_[A-Za-z0-9]{20,}\b"),
}
UNWANTED_NAMES = {
    ".DS_Store",
    "__pycache__",
    "batch-font-context.json",
}
UNWANTED_PREFIXES = ("._",)


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md does not start with YAML frontmatter")
    try:
        block = text.split("---\n", 2)[1]
    except IndexError as exc:
        raise ValueError("SKILL.md frontmatter is not closed") from exc
    data = yaml.safe_load(block)
    if not isinstance(data, dict):
        raise ValueError("SKILL.md frontmatter is not a mapping")
    return data


def check(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in sorted(REQUIRED):
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    skill_md = root / "skill-install-auditor" / "SKILL.md"
    if skill_md.is_file():
        try:
            metadata = _frontmatter(skill_md)
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
            errors.append(str(exc))
        else:
            if metadata.get("name") != "skill-install-auditor":
                errors.append("SKILL.md name must be skill-install-auditor")
            if not isinstance(metadata.get("description"), str):
                errors.append("SKILL.md description is missing")

    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.name in UNWANTED_NAMES:
            errors.append(f"unwanted generated artifact: {relative}")
        if path.name.startswith(UNWANTED_PREFIXES):
            errors.append(f"unwanted metadata sidecar: {relative}")
        if path.is_symlink():
            errors.append(f"release tree must not contain symlinks: {relative}")
        if not path.is_file() or relative in SKIP_CONTENT_CHECK:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for label, pattern in PRIVATE_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{label} found in {relative}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    errors = check(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("release hygiene check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
