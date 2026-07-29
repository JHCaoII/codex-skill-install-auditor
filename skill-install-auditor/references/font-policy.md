# CJK font policy

Use this reference only after the user selects the output language, region, and
target platform. Treat these families as starting points, not guarantees;
verify that the chosen font is installed, discoverable by the renderer, and
covers representative text.

| Target | macOS candidates | Windows candidates | Portable candidates |
| --- | --- | --- | --- |
| `zh-Hans` | PingFang SC | Microsoft YaHei | Noto Sans CJK SC / Source Han Sans SC |
| `zh-Hant-TW` | PingFang TC | Microsoft JhengHei | Noto Sans CJK TC / Source Han Sans TC |
| `zh-Hant-HK` | PingFang HK | Microsoft JhengHei with verified HK glyphs | Noto Sans CJK HK / Source Han Sans HC |
| `ja-JP` | Hiragino Sans | Yu Gothic / Meiryo | Noto Sans CJK JP / Source Han Sans JP |
| `ko-KR` | Apple SD Gothic Neo | Malgun Gothic | Noto Sans CJK KR / Source Han Sans KR |

For Linux, prefer a portable family known to be installed in the target image.
For cross-platform output, define an ordered fallback stack instead of naming
one OS-specific font.

Before proposing a repair:

1. Locate the effective assignment rather than matching comments or examples.
2. Preserve brand or Latin display fonts when they are not causing missing
   glyphs; add a language-appropriate fallback where possible.
3. For DOCX/PPTX, verify OOXML `eastAsia` assignments and language tags.
4. For CSS/HTML, update a scoped `font-family` stack, not every declaration.
5. Verify representative text for the selected locale in the actual renderer.
6. Show a dry-run diff and wait for approval before editing the staged copy.

Do not download or install fonts, modify system font settings, or write directly
to a plugin cache as part of an automatic repair.
