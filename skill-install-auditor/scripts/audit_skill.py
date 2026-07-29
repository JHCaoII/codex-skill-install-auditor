#!/usr/bin/env python3
"""Read-only compatibility and safety audit for a staged Codex Skill."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from manage_batch import load_context


TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".conf",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
CODE_SUFFIXES = {".js", ".jsx", ".mjs", ".py", ".sh", ".ts", ".tsx"}
FONT_SUFFIXES = {".otf", ".ttc", ".ttf", ".woff", ".woff2"}
SKIP_DIRS = {".git", "__pycache__", "dist", "node_modules", "tests"}
EXTERNAL_COMMANDS = {"ffmpeg", "git", "node", "npm", "npx", "rg", "soffice"}
MAX_TEXT_BYTES = 2 * 1024 * 1024
LARGE_FILE_BYTES = 25 * 1024 * 1024
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEVERITY_ORDER = {"info": 0, "medium": 1, "high": 2, "critical": 3}
CJK_MAC_FONT_RE = re.compile(
    r"PingFang|Heiti SC|Hiragino(?: Sans| Kaku Gothic| Mincho)|"
    r"Hiragino Kaku|Apple SD Gothic",
    re.I,
)
CJK_WINDOWS_FONT_RE = re.compile(
    r"Microsoft YaHei|SimHei|SimSun|Microsoft JhengHei|PMingLiU|"
    r"MingLiU|Meiryo|MS (?:Gothic|Mincho)|Yu (?:Gothic|Mincho)|"
    r"Malgun Gothic|Batang|Gulim",
    re.I,
)
CJK_PORTABLE_FONT_RE = re.compile(
    r"Noto (?:Sans|Serif)(?: CJK| (?:SC|TC|JP|KR))|"
    r"Source Han (?:Sans|Serif)|IPA(?:ex)?(?:Gothic|Mincho)|"
    r"Nanum(?:Gothic|Myeongjo)",
    re.I,
)
CJK_GENERIC_FONT_RE = re.compile(
    r"Noto (?:Sans|Serif) CJK(?!\s+(?:SC|TC|HK|JP|KR))|"
    r"Source Han (?:Sans|Serif)(?!\s+(?:SC|TC|HC|HK|JP|KR))",
    re.I,
)
CJK_LANGUAGE_FONT_RE = {
    "zh-Hans": re.compile(
        r"PingFang SC|Heiti SC|Microsoft YaHei|SimHei|SimSun|"
        r"Noto (?:Sans|Serif)(?: CJK)? SC|Source Han (?:Sans|Serif) SC",
        re.I,
    ),
    "zh-Hant-TW": re.compile(
        r"PingFang TC|Microsoft JhengHei|PMingLiU|MingLiU|"
        r"Noto (?:Sans|Serif)(?: CJK)? TC|Source Han (?:Sans|Serif) TC",
        re.I,
    ),
    "zh-Hant-HK": re.compile(
        r"PingFang HK|Noto (?:Sans|Serif)(?: CJK)? HK|"
        r"Source Han (?:Sans|Serif) (?:HC|HK)",
        re.I,
    ),
    "ja-JP": re.compile(
        r"Hiragino|Meiryo|MS (?:Gothic|Mincho)|Yu (?:Gothic|Mincho)|"
        r"Noto (?:Sans|Serif)(?: CJK)? JP|Source Han (?:Sans|Serif) JP|"
        r"IPA(?:ex)?(?:Gothic|Mincho)",
        re.I,
    ),
    "ko-KR": re.compile(
        r"Apple SD Gothic|Malgun Gothic|Batang|Gulim|"
        r"Noto (?:Sans|Serif)(?: CJK)? KR|Source Han (?:Sans|Serif) KR|"
        r"Nanum(?:Gothic|Myeongjo)",
        re.I,
    ),
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    file: str | None = None
    line: int | None = None


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _frontmatter(path: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return {}, [f"Cannot read SKILL.md: {exc}"]

    if not lines or lines[0].strip() != "---":
        return {}, ["SKILL.md must start with YAML frontmatter"]
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return {}, ["SKILL.md frontmatter is not closed"]

    values: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.startswith((" ", "\t")):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip("\"'")
    return values, errors


def _iter_files(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        current_path = Path(current)
        for name in files:
            yield current_path / name


def _read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _line_number(text: str, start: int) -> int:
    return text.count("\n", 0, start) + 1


def _python_dependencies(path: Path, text: str) -> set[str]:
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".", 1)[0])
    return modules


def _python_external_commands(path: Path, text: str) -> set[str]:
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return set()

    commands: set[str] = set()
    subprocess_calls = {
        "call",
        "check_call",
        "check_output",
        "Popen",
        "run",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function = node.func
        if not isinstance(function, ast.Attribute) or function.attr not in subprocess_calls:
            continue
        first = node.args[0]
        value: str | None = None
        if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
            head = first.elts[0]
            if isinstance(head, ast.Constant) and isinstance(head.value, str):
                value = head.value
        elif isinstance(first, ast.Constant) and isinstance(first.value, str):
            value = first.value.strip().split(maxsplit=1)[0] if first.value.strip() else None
        if value:
            command = os.path.basename(value)
            if command in EXTERNAL_COMMANDS:
                commands.add(command)
    return commands


def _language_group(tag: str) -> str | None:
    normalized = tag.strip().lower().replace("_", "-")
    if normalized in {"none", "other"}:
        return None
    if normalized.startswith(("zh-hant-hk", "zh-hk")):
        return "zh-Hant-HK"
    if normalized.startswith(("zh-hant", "zh-tw")):
        return "zh-Hant-TW"
    if normalized.startswith(("zh-hans", "zh-cn", "zh-sg")):
        return "zh-Hans"
    if normalized.startswith("ja"):
        return "ja-JP"
    if normalized.startswith("ko"):
        return "ko-KR"
    return None


def audit(
    root: Path,
    installed_root: Path,
    font_context_path: Path | None = None,
) -> dict:
    root = root.expanduser().resolve()
    installed_root = installed_root.expanduser().resolve()
    findings: list[Finding] = []
    font_context: dict | None = None
    font_context_error: str | None = None

    def add(
        severity: str,
        code: str,
        message: str,
        path: Path | None = None,
        line: int | None = None,
    ) -> None:
        findings.append(
            Finding(
                severity,
                code,
                message,
                _relative(path, root) if path else None,
                line,
            )
        )

    if font_context_path is not None:
        font_context, font_context_error = load_context(
            font_context_path.expanduser().resolve()
        )
        if font_context_error:
            add(
                "medium",
                "invalid-font-context",
                f"The local installation-batch font context cannot be reused: {font_context_error}.",
            )

    if not root.is_dir():
        add("critical", "invalid-root", "Audit target is not a directory.")
        result = _result(root, findings)
        result["font_context"] = font_context
        return result

    skill_md = root / "SKILL.md"
    skill_name = ""
    skill_description = ""
    if not skill_md.is_file():
        add("critical", "missing-skill-md", "Required SKILL.md is missing.")
    else:
        metadata, errors = _frontmatter(skill_md)
        for error in errors:
            add("critical", "invalid-frontmatter", error, skill_md)
        skill_name = metadata.get("name", "")
        description = metadata.get("description", "")
        skill_description = description
        if not skill_name:
            add("critical", "missing-name", "Frontmatter name is missing.", skill_md)
        elif not NAME_RE.fullmatch(skill_name):
            add("high", "invalid-name", "Skill name is not lowercase hyphen-case.", skill_md)
        if not description:
            add("high", "missing-description", "Frontmatter description is missing.", skill_md)
        allowed_frontmatter = {
            "name",
            "description",
            "license",
            "allowed-tools",
            "metadata",
        }
        extra = sorted(set(metadata) - allowed_frontmatter)
        if extra:
            add(
                "medium",
                "extra-frontmatter",
                "Frontmatter contains nonstandard top-level keys: " + ", ".join(extra),
                skill_md,
            )
        try:
            body = skill_md.read_text(encoding="utf-8")
            if "[TODO" in body or "TODO:" in body:
                add("high", "template-placeholder", "Unresolved TODO template text remains.", skill_md)
        except (OSError, UnicodeError):
            pass

    if skill_name:
        existing = installed_root / skill_name
        if existing.exists() and existing.resolve() != root:
            add(
                "high",
                "duplicate-installed-name",
                f"An installed Skill named '{skill_name}' already exists; treat this as an update and preserve rollback.",
            )

    text_files: list[tuple[Path, str]] = []
    font_files: list[Path] = []
    python_imports: set[str] = set()
    referenced_commands: set[str] = set()
    local_modules: set[str] = set()
    manifest_present = False

    for path in _iter_files(root):
        try:
            size = path.lstat().st_size
        except OSError:
            continue

        if path.is_symlink():
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(root)
            except (OSError, ValueError):
                add(
                    "high",
                    "escaping-symlink",
                    "Symlink resolves outside the staged Skill or is broken.",
                    path,
                )
            continue

        if size > LARGE_FILE_BYTES:
            add(
                "medium",
                "large-file",
                f"File is larger than {LARGE_FILE_BYTES // (1024 * 1024)} MiB; confirm it is necessary.",
                path,
            )
        if path.suffix.lower() in FONT_SUFFIXES:
            font_files.append(path)
        if path.name in {
            "requirements.txt",
            "pyproject.toml",
            "Pipfile",
            "package.json",
            "environment.yml",
        }:
            manifest_present = True
        if path.suffix.lower() == ".py":
            local_modules.add(path.stem)

        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = _read_text(path)
        if text is None:
            continue
        text_files.append((path, text))
        if path.suffix.lower() == ".py":
            python_imports.update(_python_dependencies(path, text))
            referenced_commands.update(_python_external_commands(path, text))
        elif path.suffix.lower() == ".sh":
            for line in text.splitlines():
                match = re.match(r"^\s*(?:env\s+)?([A-Za-z0-9_.-]+)\b", line)
                if match and match.group(1) in EXTERNAL_COMMANDS:
                    referenced_commands.add(match.group(1))
        elif path.suffix.lower() in {".js", ".jsx", ".mjs", ".ts", ".tsx"}:
            for match in re.finditer(
                r"\b(?:execFile|spawn)\s*\(\s*[\"']([^\"']+)[\"']", text
            ):
                command = os.path.basename(match.group(1))
                if command in EXTERNAL_COMMANDS:
                    referenced_commands.add(command)

    combined = "\n".join(text for _, text in text_files)
    combined_lower = combined.lower()
    executable_context = "\n".join(
        text
        for path, text in text_files
        if path.suffix.lower() not in {".md", ".txt"}
    ).lower()

    risky_patterns = [
        ("critical", "hardcoded-secret", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,})\b"), "Possible hard-coded credential detected."),
        ("high", "recursive-delete", re.compile(r"\brm\s+(?:-[A-Za-z]*r[A-Za-z]*f|-rf|-fr)\b"), "Recursive forced deletion command detected."),
        ("high", "privilege-escalation", re.compile(r"(?m)^\s*sudo\s+"), "Privilege escalation command detected."),
        ("high", "download-execute", re.compile(r"(?:curl|wget)[^\n|]{0,300}\|\s*(?:sh|bash|zsh)\b"), "Download-and-execute pipeline detected."),
        ("high", "world-writable", re.compile(r"\bchmod\s+(?:-R\s+)?777\b"), "World-writable permission command detected."),
        ("medium", "dynamic-eval", re.compile(r"\beval\s*\("), "Dynamic eval call requires review."),
        ("high", "hardcoded-user-path", re.compile(r"(?:/" + r"Users/[^/\s\"']+/|[A-Za-z]:\\\\" + r"Users\\\\[^\\\\\s\"']+\\\\)"), "User-specific absolute path detected."),
        ("medium", "hardcoded-volume-path", re.compile(r"/" + r"Volumes/[^/\n\"']+/"), "External-volume path detected."),
        ("high", "plugin-cache-write", re.compile(r"\.codex/" + r"plugins/cache"), "Direct dependency on the Codex plugin cache detected."),
        ("medium", "homebrew-path", re.compile(r"(?:/opt/" + r"homebrew/|/usr/local/(?:bin|opt)/)"), "Platform-specific package-manager path detected."),
    ]

    for path, text in text_files:
        suffix = path.suffix.lower()
        for severity, code, pattern, message in risky_patterns:
            for match in pattern.finditer(text):
                adjusted = severity
                if suffix in {".md", ".txt"} and severity != "critical":
                    adjusted = "medium"
                add(adjusted, code, message, path, _line_number(text, match.start()))

    render_context = any(
        token in (skill_description.lower() + "\n" + executable_context)
        for token in (
            "docx",
            "libreoffice",
            "soffice",
            "render_docx",
            "pptx",
            "pdf",
            "font-family",
            "pillow",
            "svg",
            "canvas",
            "subtitle",
        )
    )
    if render_context and font_context is None:
        add(
            "medium",
            "font-context-required",
            "Ask once for this installation batch's output language/region and target platform, store the selection only in the local temporary batch context, then re-run the audit with --font-context.",
        )
    home_override = bool(
        re.search(r"(?:env|os\.environ)\s*\[\s*[\"']HOME[\"']\s*\]\s*=", combined)
        or re.search(r"[\"']HOME[\"']\s*:\s*", combined)
    )
    uses_soffice = "soffice" in combined_lower or "libreoffice" in combined_lower
    has_fontconfig = bool(
        re.search(r"fontconfig(?:_file|_path)?|fonts\.conf|xdg_config_home", combined_lower)
    )
    if render_context and uses_soffice and home_override and not has_fontconfig:
        add(
            "high",
            "isolated-home-font-loss",
            "Headless LibreOffice changes HOME without preserving fontconfig; user or CJK fonts may render as missing-glyph boxes.",
        )

    has_mac_font = bool(CJK_MAC_FONT_RE.search(combined))
    has_windows_font = bool(CJK_WINDOWS_FONT_RE.search(combined))
    has_cross_font = bool(CJK_PORTABLE_FONT_RE.search(combined))
    if render_context and (has_mac_font or has_windows_font) and not has_cross_font:
        target_platform = font_context.get("platform") if font_context else None
        platform_mismatch = (
            (target_platform == "macos" and has_windows_font and not has_mac_font)
            or (target_platform == "windows" and has_mac_font and not has_windows_font)
            or (target_platform in {"linux", "cross-platform"} and has_mac_font != has_windows_font)
        )
        if platform_mismatch:
            add(
                "medium",
                "target-platform-font-mismatch",
                f"Named CJK fonts do not provide a verified fallback for the selected target platform ({target_platform}).",
            )
        elif target_platform is None and has_mac_font != has_windows_font:
            add(
                "medium",
                "single-platform-cjk-font",
                "CJK rendering names only one platform font and has no portable or opposite-platform fallback; verify simplified/traditional Chinese, Japanese, and Korean coverage.",
            )

    if render_context and font_context:
        requested_groups = {
            group
            for language in font_context["languages"]
            if (group := _language_group(language)) is not None
        }
        named_cjk_font = has_mac_font or has_windows_font or has_cross_font
        if requested_groups and named_cjk_font and not CJK_GENERIC_FONT_RE.search(combined):
            missing_groups = sorted(
                group
                for group in requested_groups
                if not CJK_LANGUAGE_FONT_RE[group].search(combined)
            )
            if missing_groups:
                add(
                    "medium",
                    "target-language-font-mismatch",
                    "No language-appropriate named font was found for: "
                    + ", ".join(missing_groups)
                    + ". Verify the effective assignment and fallback chain.",
                )
    if render_context and (has_mac_font or has_windows_font or has_cross_font):
        if "eastasia" not in combined_lower:
            add(
                "medium",
                "missing-eastasia-font",
                "CJK font assignment is present but no OOXML eastAsia font assignment was found.",
            )

    if font_files:
        license_present = any(
            path.name.lower().startswith(("license", "ofl")) for path, _ in text_files
        )
        if not license_present:
            add(
                "high",
                "font-license-missing",
                "Bundled font files were found without a LICENSE or OFL file.",
            )

    stdlib = set(getattr(sys, "stdlib_module_names", set())) | {
        "argparse",
        "ast",
        "collections",
        "contextlib",
        "csv",
        "dataclasses",
        "datetime",
        "functools",
        "glob",
        "hashlib",
        "html",
        "importlib",
        "io",
        "itertools",
        "json",
        "logging",
        "math",
        "os",
        "pathlib",
        "platform",
        "re",
        "shlex",
        "shutil",
        "sqlite3",
        "subprocess",
        "sys",
        "tempfile",
        "textwrap",
        "time",
        "typing",
        "urllib",
        "uuid",
        "xml",
        "zipfile",
    }
    third_party = sorted(
        module
        for module in python_imports
        if module not in stdlib and module not in local_modules and module != "__future__"
    )
    if third_party and not manifest_present:
        add(
            "medium",
            "undeclared-python-dependencies",
            "Python imports appear undeclared: " + ", ".join(third_party[:12]),
        )

    for command in sorted(referenced_commands):
        if shutil.which(command) is None:
            add(
                "medium",
                "missing-external-command",
                f"Referenced external command is not on the current PATH: {command}",
            )

    model_versions = sorted(set(re.findall(r"\bgpt-\d+(?:\.\d+){0,2}\b", combined_lower)))
    if model_versions:
        add(
            "info",
            "hardcoded-model-version",
            "Hard-coded model names found; confirm they remain intentional: "
            + ", ".join(model_versions[:8]),
        )

    if re.search(r"https?://", combined):
        add(
            "info",
            "network-reference",
            "Network URLs are referenced; confirm offline behavior and trust boundaries.",
        )

    result = _result(root, findings)
    result["font_context"] = font_context
    return result


def _result(root: Path, findings: list[Finding]) -> dict:
    findings.sort(
        key=lambda item: (
            -SEVERITY_ORDER[item.severity],
            item.file or "",
            item.line or 0,
            item.code,
        )
    )
    highest = max((SEVERITY_ORDER[item.severity] for item in findings), default=0)
    status = "BLOCK" if highest >= 3 else "REVIEW" if highest >= 1 else "PASS"
    counts = {
        severity: sum(item.severity == severity for item in findings)
        for severity in ("critical", "high", "medium", "info")
    }
    return {
        "target": str(root),
        "status": status,
        "counts": counts,
        "findings": [asdict(item) for item in findings],
    }


def _print_human(result: dict) -> None:
    counts = result["counts"]
    print(f"Skill audit: {result['target']}")
    print(
        "Status: "
        f"{result['status']} "
        f"(critical={counts['critical']}, high={counts['high']}, "
        f"medium={counts['medium']}, info={counts['info']})"
    )
    if not result["findings"]:
        print("No findings.")
        return
    for finding in result["findings"]:
        location = finding["file"] or "<skill>"
        if finding["line"]:
            location += f":{finding['line']}"
        print(
            f"[{finding['severity'].upper()}] {finding['code']} "
            f"{location} — {finding['message']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit a staged Codex Skill without modifying it."
    )
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument(
        "--installed-root",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills",
    )
    parser.add_argument(
        "--font-context",
        type=Path,
        help="Local, expiring installation-batch context created by manage_batch.py.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = audit(args.skill_dir, args.installed_root, args.font_context)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)

    if result["status"] == "BLOCK":
        return 3
    if result["status"] == "REVIEW":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
