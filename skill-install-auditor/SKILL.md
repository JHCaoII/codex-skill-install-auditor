---
name: skill-install-auditor
description: Audit a downloaded Codex Skill, or Skill content bundled with a plugin, before installation, update, import, migration, copying, or enablement. Detect safety, portability, dependency, and CJK font-rendering risks; when rendering is relevant, ask once per local installation batch for the target language, region, and platform, then reuse that context for consecutive installs.
---

# Skill installation audit

Keep a candidate Skill inactive until it passes review.

This audit covers failures that can be mistaken for application defects. In
particular, missing CJK glyphs, unsuitable fallback fonts, and inaccessible
font configuration can make generated documents or images look broken and may
lead an agent to repeat diagnosis or edits that cannot fix the actual problem.

## Workflow

1. Create one local staging root for the installation batch. Put each candidate
   in its own directory under that root; do not install directly into
   `~/.codex/skills`.
2. Run the read-only auditor on the first candidate:

   ```bash
   python scripts/audit_skill.py /absolute/path/to/staged-skill
   ```

3. If it reports `font-context-required`, ask exactly once for the batch:

   > 为了判断本批次安装的 Skill 是否可能出现字体兼容问题，请选择预计使用的语言、地区和运行平台。本批次后续安装将复用这些选项，不再重复询问。相关选项仅写入本地安装批次的临时配置，不会由本 Skill 主动上传；批次结束或配置过期后不再使用。

   Accept multiple languages. Distinguish `zh-Hans`, `zh-Hant-TW`,
   `zh-Hant-HK`, `ja-JP`, and `ko-KR`; also accept another BCP 47 tag or
   `none`. Record the target platform as `macos`, `windows`, `linux`, or
   `cross-platform`:

   ```bash
   python scripts/manage_batch.py set /absolute/path/to/batch-font-context.json \
     --language zh-Hans --platform macos
   ```

   The configuration expires two hours after creation. Reuse it for later
   candidates in the same batch without asking again:

   ```bash
   python scripts/audit_skill.py /absolute/path/to/next-skill \
     --font-context /absolute/path/to/batch-font-context.json
   ```

   Briefly state the reused selection. Ask again only when the user requests a
   change, the candidate explicitly targets a conflicting language or
   platform, the context expires, or a new batch begins. Do not claim that the
   Codex conversation itself is stored only locally.
4. Interpret the result:
   - `PASS` / exit `0`: continue with normal validation and activation.
   - `REVIEW` / exit `2`: tell the user what was found, its impact, and the
     recommended treatment. Wait for approval before modifying or activating.
   - `BLOCK` / exit `3`: do not activate. Report the blocking problem first.
5. After approval, repair only the staged copy. Inspect the effective font
   assignment; never globally replace every matching font name. Prefer a
   verified primary font plus fallback chain over one universal default.
6. Run `quick_validate.py`, relevant dependency checks, and at least one
   realistic smoke test. Re-run the auditor after every compatibility repair.
7. Activate only the reviewed copy. For updates, preserve the working version
   until the replacement passes and can be rolled back safely.

An installation request already authorizes activation when the audit passes
without compatibility findings. Do not add an unnecessary confirmation in that
case.

## Review priorities

Pay particular attention to:

- CJK font coverage and fallbacks for simplified Chinese, traditional Chinese
  (`zh-TW` / `zh-HK`), Japanese, and Korean. Do not treat the absence of
  missing-glyph boxes as proof of correctness: traditional-Chinese locale
  glyphs may still be wrong.
- Headless LibreOffice, temporary `HOME`, fontconfig, and platform font
  fallbacks. Treat a fontconfig finding as a compatibility risk, not proof
  that a render will fail.
- Font findings that can plausibly cause repeated agent diagnosis or edits;
  distinguish missing glyphs, locale-glyph mismatch, and an actual code error.
- The selected language, region, target platform, actual font discoverability,
  and representative character coverage. User language is not automatically
  the candidate's output language.
- Hard-coded user, volume, plugin-cache, Homebrew, and Windows paths.
- Undeclared Python dependencies and unavailable external commands.
- Embedded font files without a license.
- Destructive shell commands, privilege escalation, download-and-execute
  pipelines, hard-coded secrets, and escaping symlinks.
- Duplicate installed names, unresolved template placeholders, oversized
  assets, and hard-coded model versions.

Treat static findings as evidence for review, not automatic permission to edit.
Explain likely false positives instead of silently suppressing them.

Read [references/font-policy.md](references/font-policy.md) only when a font
finding needs interpretation or a staged repair needs a fallback recommendation.

## Scope

Do not scan installed Skills repeatedly or load this workflow for ordinary
document, image, video, website, or coding tasks. Re-run it only when a Skill is
installed, updated, imported, migrated, enabled, or explicitly audited.

This workflow audits Codex Skill directories, including Skill content bundled
with a plugin. A standalone plugin, MCP server, application, or package-manager
bundle without a `SKILL.md` is outside the current script format and should be
reviewed with the appropriate package-specific process.

Initially make targeted font repairs only in CSS/HTML, `python-docx`,
`python-pptx`, and headless LibreOffice workflows. For SVG, Canvas, Pillow,
video subtitles, or other renderers, report the risk until a format-specific
repair can be validated. Never install fonts, modify system font settings, or
write plugin caches without separate user authorization.
