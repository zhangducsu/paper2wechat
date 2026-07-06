# PDF论文 → 微信公众号文章 Agent工作组

基于 Claude Code 多 Agent 架构的学术论文科普文章自动化生成工具。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

依赖包含 PDF 提取、Markdown 解析和 HTML 后处理所需组件。

### 2. 环境检查

Windows PowerShell 推荐先运行：

```powershell
powershell -ExecutionPolicy Bypass -File .claude/scripts/doctor.ps1
```

其他环境：

```bash
python .claude/scripts/check_env.py --json-output .claude/tmp/env_status.json
```

检查通过后，JSON 输出中的 `status` 应为 `pass`。

### 3. 使用

在 Claude Code 中执行：

```
/paper2wechat path/to/your/paper.pdf
```

工作流自动完成：环境检查 → 确定性提取PDF → 确认风格 → 撰写Markdown → 选主题 → 渲染HTML → 生成封面图 → 审核与校验 → 输出

Markdown 渲染支持标题、列表、表格、代码块、图片、脚注、任务列表、高亮标记，以及行内/块级公式的微信兼容文本呈现。

推文主题色从公司 Logo 自动提取；Logo 含多种颜色时，会围绕主色生成匹配的和谐色系。

封面背景由 AI 生图功能生成，脚本再用本地 PIL 叠加标题和公司 Logo 水印；默认输出 `900x383` 封面和 `383x383` 方图。

### 4. 质量门禁

本地提交前建议运行：

```bash
python .claude/scripts/run_quality_checks.py
```

该命令会依次执行环境检查、语法编译、单元测试、fixture 渲染和产物校验，并输出 `.claude/tmp/quality_report.json`。

### 5. 发布到微信公众号

1. 浏览器打开生成的 HTML → `Ctrl+A` 全选 → `Ctrl+C` 复制
2. 微信公众号编辑器 → `Ctrl+V` 粘贴
3. 上传图片 → 预览 → 发布

## 命令

| 命令 | 说明 |
|------|------|
| `/paper2wechat` | 完整工作流：PDF → 微信文章 |
| `/extract-style` | 从推文提取样式模板 + 拆解写作技巧 |
| `/analyze-article` | 纯写作技巧拆解 |

## 项目结构

```
.claude/
├── commands/          # 斜杠命令（3个）
├── agents/            # Agent定义（3个）
├── scripts/           # Python/PowerShell/JS脚本
├── templates/         # 知识库 + 排版主题
│   ├── references/    # 写作技巧、结构模板、质检清单、企业信息
│   └── themes/        # doocs主题 + 自定义模板
└── 部署指南.md        # 完整部署文档
```

关键脚本：

| 脚本 | 说明 |
|------|------|
| `.claude/scripts/doctor.ps1` | Windows PowerShell 环境检查入口 |
| `.claude/scripts/check_env.py` | 检查 Python、依赖、目录可写性、可选 MCP 配置 |
| `.claude/scripts/extract_content.py` | PDF → content.json/full_text/figures/run_state |
| `.claude/scripts/generate_cover.py` | 基于 AI 生图背景合成微信公众号封面图，添加公司 Logo 水印 |
| `.claude/scripts/md2wechat.py` | Markdown → 微信兼容 HTML，使用 Markdown 库解析并注入内联样式 |
| `.claude/scripts/run_quality_checks.py` | 本地/CI 共用质量门禁入口 |
| `.claude/scripts/sync_assets.py` | 复制全局素材到 figures，并规范 Markdown 图片路径 |
| `.claude/scripts/theme_palette.py` | 从公司 Logo 提取主题色并生成和谐色系 |
| `.claude/scripts/validate_run.py` | 校验 content、Markdown、HTML 图片引用与微信兼容性 |

## 详细文档

完整的部署步骤、配置说明、自定义方法和常见问题，请查看 [部署指南.md](./部署指南.md)。
