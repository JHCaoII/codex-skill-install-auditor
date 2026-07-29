# Codex Skill Install Auditor

Audit a Codex Skill before installation, with special attention to CJK font
compatibility, isolated rendering environments, portability, dependencies, and
unsafe operations.

The auditor is designed to catch failures that can look like application bugs:
missing-glyph boxes, unsuitable regional glyphs, unavailable font fallbacks,
and fonts that disappear when a renderer changes `HOME` or fontconfig. These
failures can otherwise cause an agent to repeat ineffective code changes.

## Highlights

- Read-only static audit with `PASS`, `REVIEW`, and `BLOCK` results.
- CJK checks for simplified Chinese, Taiwan traditional Chinese, Hong Kong
  traditional Chinese, Japanese, and Korean.
- Platform-aware font findings for macOS, Windows, Linux, and cross-platform
  targets.
- Local, expiring language and platform context reused across consecutive
  installation audits.
- Checks for dangerous commands, hard-coded secrets and paths, undeclared
  dependencies, missing font licenses, and escaping symlinks.
- No runtime dependencies for the auditor itself; Python 3.9 or newer is
  sufficient.

## Install

Copy the distributable `skill-install-auditor` directory into your Codex Skill
directory:

```bash
cp -R skill-install-auditor "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Restart or refresh Codex so it discovers the exact `SKILL.md` filename.

## Basic usage

Stage a candidate Skill and run:

```bash
python skill-install-auditor/scripts/audit_skill.py /path/to/staged-skill
```

For a rendering-related candidate, the first result may request a local font
context. Create it once for the installation batch:

```bash
python skill-install-auditor/scripts/manage_batch.py set \
  /path/to/batch-font-context.json \
  --language zh-Hans \
  --platform macos
```

Reuse the same local context for subsequent candidates:

```bash
python skill-install-auditor/scripts/audit_skill.py \
  /path/to/next-staged-skill \
  --font-context /path/to/batch-font-context.json
```

Use `--json` for structured output. `PASS`, `REVIEW`, and `BLOCK` correspond to
exit codes `0`, `2`, and `3`.

## Privacy and safety

The batch context contains only selected language tags, target platform, and
timestamps. It is written to the local path chosen by the operator and expires
after two hours by default. The Skill does not upload it.

The auditor never installs fonts or dependencies, changes system font settings,
or writes into plugin caches. A `REVIEW` result is evidence for human review,
not permission to edit. Apply approved repairs only to a staged copy.

## Current scope

The script audits directories that contain `SKILL.md`, including Skill content
bundled within a plugin. Standalone plugin and MCP package formats are not yet
supported. Font repair guidance initially targets CSS/HTML, `python-docx`,
`python-pptx`, and headless LibreOffice; other renderers are reported for
manual review.

Static analysis cannot guarantee runtime behavior or perfect glyph selection.
Confirm font discoverability and render representative text in the actual
target environment.

## Development

Install the validation dependency and run the checks:

```bash
python -m pip install -r requirements-dev.txt
python skill-install-auditor/tests/test_audit_skill.py
python tests/test_examples.py
python tools/check_release.py .
```

The GitHub Actions workflow runs these checks on macOS, Windows, and Linux.

## License

MIT. See [LICENSE](LICENSE).

## 中文简介

本项目用于在安装 Codex Skill 前检查安全性、可移植性及 CJK 字体兼容风险，重点覆盖简体中文、台湾繁体、香港繁体、日文和韩文。连续安装时，语言、地区和平台选项会保存在本地临时批次配置中并自动复用，避免重复询问。
