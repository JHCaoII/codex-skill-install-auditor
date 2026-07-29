#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).parents[1]
AUDITOR = ROOT / "skill-install-auditor" / "scripts" / "audit_skill.py"
MANAGER = ROOT / "skill-install-auditor" / "scripts" / "manage_batch.py"


def run_audit(skill: Path, installed: Path, context: Path | None = None) -> tuple[int, dict]:
    command = [
        sys.executable,
        str(AUDITOR),
        str(skill),
        "--installed-root",
        str(installed),
        "--json",
    ]
    if context is not None:
        command.extend(["--font-context", str(context)])
    process = subprocess.run(command, check=False, capture_output=True, text=True)
    return process.returncode, json.loads(process.stdout)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="release_examples_") as temporary:
        work = Path(temporary)
        installed = work / "installed"
        installed.mkdir()

        code, result = run_audit(ROOT / "examples" / "portable-skill", installed)
        assert code == 0, result
        assert result["status"] == "PASS", result

        risky = ROOT / "examples" / "cjk-risk-skill"
        code, result = run_audit(risky, installed)
        finding_codes = {item["code"] for item in result["findings"]}
        assert code == 2, result
        assert result["status"] == "REVIEW", result
        assert {
            "font-context-required",
            "isolated-home-font-loss",
            "single-platform-cjk-font",
        }.issubset(finding_codes), result

        context = work / "batch-font-context.json"
        subprocess.run(
            [
                sys.executable,
                str(MANAGER),
                "set",
                str(context),
                "--language",
                "zh-Hans",
                "--platform",
                "macos",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        code, result = run_audit(risky, installed, context)
        finding_codes = {item["code"] for item in result["findings"]}
        assert code == 2, result
        assert "font-context-required" not in finding_codes, result
        assert "target-language-font-mismatch" not in finding_codes, result
        assert "target-platform-font-mismatch" not in finding_codes, result

    print("release example tests passed")


if __name__ == "__main__":
    main()
