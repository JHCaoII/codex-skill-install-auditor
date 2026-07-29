# Codex Skill Install Auditor

[![test](https://github.com/JHCaoII/codex-skill-install-auditor/actions/workflows/test.yml/badge.svg)](https://github.com/JHCaoII/codex-skill-install-auditor/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

在安装、更新或启用 Codex Skill 之前，检查字体兼容、安全性、依赖、路径和跨平台风险。

它重点解决一种容易被误判为代码错误的问题：Skill 或插件在生成文档、幻灯片、图片或网页时调用了当前环境中不存在或不适合目标语言的字体，导致方框、缺字、区域字形错误或回退字体异常。智能体如果没有识别出真正原因，可能会不断修改代码和内容，却始终无法修复最终渲染结果。

`skill-install-auditor` 会先在隔离目录进行只读检查，在发现问题后给出 `PASS`、`REVIEW` 或 `BLOCK`，让兼容性问题在安装前暴露，而不是在生成结果出错后反复返工。

## 为什么需要它

一个在开发者电脑上正常工作的 Skill，换到另一台电脑、GitHub Runner、临时 `HOME`、无界面渲染环境或不同操作系统后，可能出现完全不同的字体结果。

常见原因包括：

- Skill 写死了仅存在于某个平台的字体名称。
- 简体中文、繁体中文、日文和韩文共用字体时，字形区域不匹配。
- 临时 `HOME` 或独立 fontconfig 让系统字体突然不可见。
- CSS、Office、LibreOffice 或图片渲染器使用了不同的字体回退链。
- 字体文件随项目分发，但没有许可证或来源说明。
- 智能体把字体环境问题误判成代码问题，产生重复诊断和重复修改。

这个项目的目标不是保证所有设备渲染结果完全一致，而是在 Skill 安装前找出足以导致失败、误判或重复修复的高风险条件。

## 它会检查什么

### CJK 字体兼容

- 简体中文 `zh-Hans`
- 台湾繁体中文 `zh-Hant-TW`
- 香港繁体中文 `zh-Hant-HK`
- 日文 `ja-JP`
- 韩文 `ko-KR`
- macOS、Windows、Linux 和跨平台目标
- 字体缺失、单平台字体、错误回退和区域字形不匹配
- 临时 `HOME`、fontconfig 和 headless LibreOffice 风险

### 安装与可移植性

- 写死的用户目录、外接盘、插件缓存、Homebrew 和 Windows 路径
- 未声明的 Python 依赖和不可用的外部命令
- 重复的 Skill 名称、未解析模板和逃逸目录的符号链接
- 可能被错误复制进发布包的临时文件和本机配置

### 安全风险

- 破坏性命令和权限提升
- 下载后直接执行的命令链
- 硬编码密钥或令牌
- 缺少许可证的内嵌字体
- 安装过程中可能越过隔离目录的操作

## 工作方式

1. 将待安装的 Skill 放入隔离暂存目录，不直接写入正式 Skill 目录。
2. 运行只读审计，检测安全、依赖、路径和字体风险。
3. 只有确实涉及渲染时，询问一次目标语言、地区和平台。
4. 同一批连续安装会复用本地临时选项，不会重复询问。
5. 仅在用户确认后修改暂存副本；重新验证通过后再启用。

语言与平台选项只写入用户指定的本地批次配置。默认两小时后过期，本 Skill 不会主动上传这些内容。

## 结果说明

| 结果 | 退出码 | 含义 |
| --- | ---: | --- |
| `PASS` | `0` | 未发现需要阻止安装的问题，可以继续正常验证与启用。 |
| `REVIEW` | `2` | 发现兼容性或可移植性风险，需要说明影响并由用户确认处理方案。 |
| `BLOCK` | `3` | 发现阻断性安全问题，不应安装或启用。 |

`REVIEW` 不等于确认渲染必然失败，也不授权智能体自动修改文件。它表示当前证据足以要求人工判断或实际渲染验证。

## 安装

### 使用 Codex Skill Installer

在 Codex 中运行：

```text
$skill-installer install https://github.com/JHCaoII/codex-skill-install-auditor/tree/main/skill-install-auditor
```

安装或更新任何第三方 Skill 时，建议先将候选内容下载到隔离目录，再使用本项目审计。

### 手动安装

将仓库中的 `skill-install-auditor` 目录复制到 Codex Skill 目录：

```bash
cp -R skill-install-auditor "${CODEX_HOME:-$HOME/.codex}/skills/"
```

完成后重新启动或刷新 Codex，使其重新发现 `SKILL.md`。

## 基本使用

审计一个暂存的 Skill：

```bash
python skill-install-auditor/scripts/audit_skill.py \
  /absolute/path/to/staged-skill
```

需要结构化结果时添加 `--json`：

```bash
python skill-install-auditor/scripts/audit_skill.py \
  /absolute/path/to/staged-skill \
  --json
```

如果候选 Skill 涉及渲染，首次检查可能要求提供字体环境。为当前安装批次创建一次本地配置：

```bash
python skill-install-auditor/scripts/manage_batch.py set \
  /absolute/path/to/batch-font-context.json \
  --language zh-Hans \
  --platform macos
```

连续审计后续候选 Skill 时复用该配置：

```bash
python skill-install-auditor/scripts/audit_skill.py \
  /absolute/path/to/next-staged-skill \
  --font-context /absolute/path/to/batch-font-context.json
```

## 示例

仓库提供两个最小示例：

- `examples/portable-skill`：不包含已知字体和路径风险，预期结果为 `PASS`。
- `examples/cjk-risk-skill`：包含单平台 CJK 字体和隔离环境风险，预期结果为 `REVIEW`。

这些示例同时用于 GitHub Actions 的跨平台回归测试。

## 当前边界

- 当前审计对象是包含 `SKILL.md` 的目录，包括插件内部附带的 Skill 内容。
- 尚未直接审计完整的独立插件包或 MCP Server 包。
- 字体修复指导优先覆盖 CSS/HTML、`python-docx`、`python-pptx` 和 headless LibreOffice。
- 静态检查无法代替真实渲染。重要输出仍应在目标操作系统和渲染器中使用代表性字符验证。
- 本项目不会自动安装字体、修改系统字体设置或向插件缓存写入内容。

## 项目结构

```text
skill-install-auditor/
├── SKILL.md
├── agents/
├── references/
├── scripts/
└── tests/

examples/               # PASS / REVIEW 示例
tests/                  # 发布包回归测试
tools/                  # 发布卫生检查
.github/workflows/      # macOS / Windows / Linux 测试矩阵
```

## 开发与验证

安装验证依赖：

```bash
python -m pip install -r requirements-dev.txt
```

运行本地检查：

```bash
python tools/check_release.py .
python skill-install-auditor/tests/test_audit_skill.py
python tests/test_examples.py
```

GitHub Actions 会在 macOS、Windows 和 Linux 上使用 Python 3.9 与 3.12 运行测试。

## English summary

Codex Skill Install Auditor performs a read-only pre-installation audit of downloaded Codex Skills and Skill content bundled with plugins. It focuses on CJK font compatibility, isolated rendering environments, portability, dependencies, and unsafe operations.

It detects missing or unsuitable font fallbacks for Simplified Chinese, Traditional Chinese, Japanese, and Korean, along with temporary `HOME`, fontconfig, hard-coded path, dependency, secret, symlink, and destructive-command risks. Results are reported as `PASS`, `REVIEW`, or `BLOCK`; language and platform choices are stored only in a local, expiring batch context and reused across consecutive audits.

## License

MIT. See [LICENSE](LICENSE).
