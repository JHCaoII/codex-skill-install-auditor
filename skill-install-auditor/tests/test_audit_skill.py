#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


AUDITOR = Path(__file__).parents[1] / "scripts" / "audit_skill.py"
MANAGER = Path(__file__).parents[1] / "scripts" / "manage_batch.py"


def run_audit(
    skill_dir: Path,
    installed_root: Path,
    font_context: Path | None = None,
) -> tuple[int, dict]:
    command = [
        sys.executable,
        str(AUDITOR),
        str(skill_dir),
        "--installed-root",
        str(installed_root),
        "--json",
    ]
    if font_context is not None:
        command.extend(["--font-context", str(font_context)])
    proc = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    return proc.returncode, json.loads(proc.stdout)


def set_context(path: Path, languages: list[str], platform: str) -> dict:
    command = [sys.executable, str(MANAGER), "set", str(path)]
    for language in languages:
        command.extend(["--language", language])
    command.extend(["--platform", platform])
    proc = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="skill_auditor_test_") as temp:
        root = Path(temp)
        installed = root / "installed"
        installed.mkdir()

        good = root / "portable-skill"
        (good / "scripts").mkdir(parents=True)
        (good / "SKILL.md").write_text(
            "---\n"
            "name: portable-skill\n"
            "description: Perform a portable local task when explicitly requested.\n"
            "---\n\n"
            "# Portable Skill\n\n"
            "Run the bundled script.\n",
            encoding="utf-8",
        )
        (good / "scripts" / "run.py").write_text(
            "from pathlib import Path\nprint(Path.cwd())\n",
            encoding="utf-8",
        )
        code, result = run_audit(good, installed)
        assert code == 0, result
        assert result["status"] == "PASS", result

        risky = root / "risky-renderer"
        (risky / "scripts").mkdir(parents=True)
        (risky / "SKILL.md").write_text(
            "---\n"
            "name: risky-renderer\n"
            "description: Render Chinese DOCX files with LibreOffice.\n"
            "---\n\n"
            "# Risky Renderer\n\n"
            "Use PingFang SC for every computer.\n",
            encoding="utf-8",
        )
        (risky / "scripts" / "render.py").write_text(
            "import os\n"
            "import subprocess\n"
            'env = os.environ.copy()\n'
            'env[\"HOME\"] = \"/Users/example/temp-profile\"\n'
            'subprocess.run([\"soffice\", \"--headless\", \"input.docx\"], env=env)\n'
            'subprocess.run(\"rm -rf build\", shell=True)\n',
            encoding="utf-8",
        )
        code, result = run_audit(risky, installed)
        finding_codes = {item["code"] for item in result["findings"]}
        assert code == 2, result
        assert result["status"] == "REVIEW", result
        assert {
            "font-context-required",
            "isolated-home-font-loss",
            "single-platform-cjk-font",
            "recursive-delete",
            "hardcoded-user-path",
        }.issubset(finding_codes), result

        batch_context = root / "batch-font-context.json"
        saved_context = set_context(batch_context, ["zh-Hans"], "macos")
        assert saved_context["languages"] == ["zh-Hans"], saved_context
        code, result = run_audit(risky, installed, batch_context)
        finding_codes = {item["code"] for item in result["findings"]}
        assert code == 2, result
        assert result["font_context"]["platform"] == "macos", result
        assert "font-context-required" not in finding_codes, result
        assert "target-platform-font-mismatch" not in finding_codes, result

        japanese = root / "japanese-renderer"
        japanese.mkdir()
        (japanese / "SKILL.md").write_text(
            "---\n"
            "name: japanese-renderer\n"
            "description: Render ja-JP PDF documents.\n"
            "---\n\n"
            "# Japanese Renderer\n\n"
            "Use Meiryo for all rendered Japanese text.\n",
            encoding="utf-8",
        )
        set_context(batch_context, ["ja-JP"], "windows")
        code, result = run_audit(japanese, installed, batch_context)
        finding_codes = {item["code"] for item in result["findings"]}
        assert code == 2, result
        assert "font-context-required" not in finding_codes, result
        assert "target-language-font-mismatch" not in finding_codes, result
        assert "target-platform-font-mismatch" not in finding_codes, result

        set_context(batch_context, ["zh-Hans"], "windows")
        code, result = run_audit(japanese, installed, batch_context)
        finding_codes = {item["code"] for item in result["findings"]}
        assert code == 2, result
        assert "target-language-font-mismatch" in finding_codes, result

        traditional = root / "traditional-renderer"
        traditional.mkdir()
        (traditional / "SKILL.md").write_text(
            "---\n"
            "name: traditional-renderer\n"
            "description: Render zh-Hant and zh-TW PDF documents.\n"
            "---\n\n"
            "# Traditional Chinese Renderer\n\n"
            "Use Microsoft JhengHei for all rendered text.\n",
            encoding="utf-8",
        )
        set_context(batch_context, ["zh-Hant-TW"], "windows")
        code, result = run_audit(traditional, installed, batch_context)
        finding_codes = {item["code"] for item in result["findings"]}
        assert code == 2, result
        assert "font-context-required" not in finding_codes, result
        assert "target-language-font-mismatch" not in finding_codes, result
        assert "target-platform-font-mismatch" not in finding_codes, result

        korean = root / "korean-renderer"
        korean.mkdir()
        (korean / "SKILL.md").write_text(
            "---\n"
            "name: korean-renderer\n"
            "description: Render ko-KR PDF documents.\n"
            "---\n\n"
            "# Korean Renderer\n\n"
            "Use Malgun Gothic for all rendered Korean text.\n",
            encoding="utf-8",
        )
        set_context(batch_context, ["ko-KR"], "windows")
        code, result = run_audit(korean, installed, batch_context)
        finding_codes = {item["code"] for item in result["findings"]}
        assert code == 2, result
        assert "font-context-required" not in finding_codes, result
        assert "target-language-font-mismatch" not in finding_codes, result
        assert "target-platform-font-mismatch" not in finding_codes, result

        hong_kong = root / "hong-kong-renderer"
        hong_kong.mkdir()
        (hong_kong / "SKILL.md").write_text(
            "---\n"
            "name: hong-kong-renderer\n"
            "description: Render zh-Hant-HK PDF documents.\n"
            "---\n\n"
            "# Hong Kong Renderer\n\n"
            "Use PingFang HK for all rendered Hong Kong text.\n",
            encoding="utf-8",
        )
        set_context(batch_context, ["zh-Hant-HK"], "macos")
        code, result = run_audit(hong_kong, installed, batch_context)
        finding_codes = {item["code"] for item in result["findings"]}
        assert code == 2, result
        assert "font-context-required" not in finding_codes, result
        assert "target-language-font-mismatch" not in finding_codes, result
        assert "target-platform-font-mismatch" not in finding_codes, result

        code, result = run_audit(traditional, installed, root / "missing-context.json")
        finding_codes = {item["code"] for item in result["findings"]}
        assert code == 2, result
        assert "invalid-font-context" in finding_codes, result
        assert "font-context-required" in finding_codes, result

        invalid = root / "invalid-skill"
        invalid.mkdir()
        code, result = run_audit(invalid, installed)
        assert code == 3, result
        assert result["status"] == "BLOCK", result

    print("skill-install-auditor tests passed")


if __name__ == "__main__":
    main()
