# paper2wechat 后续版本规划

## 当前版本 v1.5 状态

**已实现功能**：
- 3个Agent（extractor → writer → reviewer）
- 3个斜杠命令（/paper2wechat、/extract-style、/analyze-article）
- Markdown→HTML渲染器（md2wechat.py）
- 知识库进化机制（只追加不覆盖）
- wechat-parser-mcp集成
- doocs主题 + 自定义模板支持
- P0运行基线：`check_env.py` + `doctor.ps1` + `requirements.txt`
- P1确定性抽取链路：`extract_content.py` + `figure_map.json` + `run_state.json` + `validate_run.py`
- P2渲染基线：`md2wechat.py` 使用 Python-Markdown + BeautifulSoup，支持内联样式模板与基础安全转义
- P3质量保障基线：`run_quality_checks.py` + `tests/fixtures/` + `.github/workflows/test.yml`
- P4功能增强基线：支持数学公式、脚注、任务列表和高亮标记
- 封面生成基线：AI 生图生成封面背景，`generate_cover.py` 本地生成封面图和方图，添加公司 Logo 水印

**已知遗留问题**：
1. PDF元信息/章节解析仍是启发式，复杂版式需要人工复核
2. 数学公式当前以微信兼容文本样式呈现，不做 LaTeX 图片或 KaTeX 渲染

---

## P0/P1 — 运行与抽取基线（已落地）

### 目标
先把单篇 PDF 的运行环境、抽取状态、图片引用和校验报告固定下来，避免工作流只靠提示词维持。

### 已落地文件

| 文件 | 作用 |
|------|------|
| `requirements.txt` | 固定运行依赖 |
| `scripts/check_env.py` | 检查 Python、依赖、目录可写性和可选 MCP 配置 |
| `scripts/doctor.ps1` | Windows PowerShell 环境检查入口，绕过 WindowsApps 0字节别名 |
| `scripts/extract_content.py` | PDF → `content.json` / `full_text.txt` / `figures/` / `run_state.json` |
| `scripts/extract_figures.py` | 顺序稳定抽图、图片哈希去重、生成 `figure_map.json` |
| `scripts/sync_assets.py` | 同步全局素材到 `figures/` 并规范 Markdown 图片路径 |
| `scripts/validate_run.py` | 校验 content、Markdown、HTML 图片引用和微信兼容性基础约束 |

---

## P2 — Markdown 渲染基线（已落地）

### 目标
将 `md2wechat.py` 从手写 Markdown 解析升级为成熟库解析，减少列表、表格、代码块和 HTML 转义的不确定性。

### 已落地能力

| 文件 | 改动内容 |
|------|----------|
| `requirements.txt` | 新增 `markdown`、`beautifulsoup4` |
| `scripts/check_env.py` | 将 `markdown`、`beautifulsoup4` 纳入必需依赖检查 |
| `scripts/md2wechat.py` | 使用 Python-Markdown 解析 Markdown，使用 BeautifulSoup 注入内联样式 |
| `scripts/md2wechat.py` | 支持标准表格、嵌套列表、围栏代码块、原始 HTML 标签转义 |
| `scripts/md2wechat.py` | 自动读取自定义 CSS 同名 `_inline.json`，也支持 `--inline-template` 显式指定 |
| `tests/test_md2wechat.py` | 覆盖 HTML 转义、嵌套列表、表格、代码块、inline JSON 模板 |

---

## P3 — 质量保障基线（已落地）

### 目标
建立本地和 CI 共用的质量门禁，确保 P0/P1/P2 不因后续修改回归。

### 已落地能力

| 文件 | 改动内容 |
|------|----------|
| `scripts/run_quality_checks.py` | 统一执行环境检查、语法编译、单元测试、fixture 渲染和产物校验 |
| `tests/fixtures/` | 新增稳定 Markdown/content/图片引用样例 |
| `tests/test_quality_fixtures.py` | 验证 fixture 文章能完成渲染并通过产物校验 |
| `.github/workflows/test.yml` | GitHub Actions 自动安装依赖并运行质量门禁 |
| `README.md` | 增加本地质量门禁命令说明 |

---

## 封面生成基线（已落地）

### 目标
生成微信文章时同步生成封面图，避免人工再单独制作封面。

### 已落地能力

| 文件 | 改动内容 |
|------|----------|
| `scripts/generate_cover.py` | 基于 AI 生图背景合成 `900x383` 封面图和 `383x383` 方图 |
| `scripts/generate_cover.py` | 支持 `--background-source ai_generated` 与 `--require-ai-background` 强制 AI 背景 |
| `scripts/generate_cover.py` | 添加公司 Logo 半透明水印，报告 `logo_watermark_applied` |
| `scripts/generate_cover.py` | 报告 `background_source=ai_generated`、`ai_generated_background=true` 与 `ai_watermark=false` |
| `scripts/validate_run.py` | 增加封面图片可读性、尺寸和 AI 背景报告校验 |
| `tests/test_generate_cover.py` | 覆盖封面尺寸、方图尺寸、Logo 水印报告、AI 背景报告和无 AI 水印标记 |

---

## P4 — Markdown 功能增强基线（已落地）

### 目标
在 P2 稳定渲染基础上，扩展公众号文章常用增强语法，但保持微信兼容和可测试。

### 已落地能力

| 语法 | 示例 | 渲染策略 |
|------|------|----------|
| 行内公式 | `$AUC = TP/(TP+FN)$` | 转为带内联样式的公式文本 |
| 块级公式 | `$$...$$` | 转为块级公式文本区 |
| 脚注 | `[^1]` / `[^1]: ...` | 使用 Python-Markdown footnotes 扩展并保留锚点 |
| 任务列表 | `- [x]` / `- [ ]` | 转为 `☑` / `☐` 列表项 |
| 高亮标记 | `==关键结论==` | 转为带内联样式的 `<mark>` |

### 已落地文件

| 文件 | 改动内容 |
|------|----------|
| `scripts/md2wechat.py` | 增加 P4 语法预处理/后处理 |
| `agents/writer.md` | 增加增强语法规范和使用边界 |
| `tests/test_md2wechat.py` | 增加 P4 回归测试 |
| `tests/fixtures/sample_article.md` | 将 P4 语法纳入质量门禁 fixture |

---

## v1.6 — 稳定性修复

### 目标
继续修复抽取与渲染边缘问题，提升稳定性

### 具体改动

| 文件 | 改动内容 |
|------|----------|
| `scripts/extract_content.py` | 继续增强元信息、章节与Figure caption解析准确性 |
| `scripts/md2wechat.py` | 继续补齐边缘 Markdown 语法和微信编辑器实测兼容性 |

---

## v1.7 — 功能增强增强

### 目标
在 P4 基线之上扩展更复杂的展示能力

### 具体改动

| 文件 | 改动内容 |
|------|----------|
| `scripts/md2wechat.py` | 公式升级为图片或 KaTeX 预渲染方案 |
| `scripts/md2wechat.py` | 支持更复杂的提示框/信息块语法 |
| `templates/themes/` | 新增2-3套精选主题（科技蓝、医学绿、学术灰） |

---

## v1.8 — 批量处理

### 目标
支持批量处理多篇论文，提升效率

### 具体改动

| 文件 | 改动内容 |
|------|----------|
| `commands/paper2wechat.md` | 支持目录输入：`/paper2wechat ./papers/` 批量处理 |
| `commands/paper2wechat.md` | 新增 `--style` 参数跳过交互确认 |
| `commands/paper2wechat.md` | 新增 `--theme` 参数指定主题 |
| `scripts/batch_process.py` | 新建批量处理脚本，支持并行处理 |
| `部署指南.md` | 更新批量处理使用说明 |

---

## v1.9 — 质量保障增强

### 目标
在 P3 基线之上扩展覆盖范围，确保代码质量

### 具体改动

| 文件 | 改动内容 |
|------|----------|
| `tests/fixtures/` | 增加真实微型 PDF fixture 或生成器 |
| `tests/test_extract_content.py` | 增加 PDF → content.json 端到端测试 |
| `tests/test_md2wechat.py` | 增加更多微信编辑器兼容性回归样例 |
| `scripts/*.py` | 继续补齐类型注解和边界条件测试 |

---

## v2.0 — 架构升级

### 目标
模块化架构，支持插件扩展

### 具体改动

| 模块 | 改动内容 |
|------|----------|
| **渲染引擎插件化** | 支持自定义渲染器（Markdown/HTML/LaTeX） |
| **PDF解析器插件化** | 支持多种PDF引擎（PyMuPDF/pdfplumber/OCR） |
| **主题包系统** | 支持主题包导入导出 |
| **知识库同步** | 支持知识库导入导出、版本控制 |

### 架构设计

```
paper2wechat/
├── core/
│   ├── extractor_base.py    # PDF提取基类
│   ├── writer_base.py       # 文章撰写基类
│   └── renderer_base.py     # 渲染器基类
├── plugins/
│   ├── extractors/
│   │   ├── pymupdf.py
│   │   └── ocr.py
│   ├── renderers/
│   │   ├── md2wechat.py
│   │   └── latex2wechat.py
│   └── themes/
│       └── theme_pack_loader.py
```

---

## 版本路线图

```
v1.6 稳定性修复 ──→ v1.7 功能增强 ──→ v1.8 批量处理
      │                   │                  │
      └───────────────────┴──────────────────┘
                          │
                    v1.9 质量保障
                          │
                    v2.0 架构升级
```

---

## 推荐优先级

1. **v1.6 稳定性修复** — 修复已知问题，提升稳定性
2. **v1.9 质量保障** — 建立测试体系，为后续开发保驾护航
3. **v1.7 功能增强** — 扩展Markdown语法支持
4. **v1.8 批量处理** — 提升效率
5. **v2.0 架构升级** — 长期演进
