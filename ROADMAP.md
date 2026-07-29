# Roadmap

## Near term

- Validate representative glyph coverage with optional, platform-appropriate
  font inspection tools.
- Add real render smoke tests for CSS/HTML, `python-docx`, `python-pptx`, and
  headless LibreOffice.
- Expand false-positive fixtures for comments, documentation examples, and
  fonts mentioned but not selected.
- Improve detection of the effective font assignment instead of relying only
  on aggregate text evidence.

## Later

- Add adapters for Pillow, SVG, Canvas, and subtitle renderers.
- Support standalone plugin and MCP package layouts without assuming
  `SKILL.md`.
- Produce format-specific dry-run patches for approved staged repairs.
- Add optional JSON Schema documentation for audit output.

## Non-goals

- Automatically downloading or installing fonts.
- Modifying system font settings or plugin caches.
- Claiming that static analysis guarantees safe runtime behavior.
