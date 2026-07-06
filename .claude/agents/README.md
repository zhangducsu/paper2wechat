# Agent 架构说明

## 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                  主编排命令 (paper2wechat.md)                 │
└────────┬──────────────────┬──────────────────┬───────────────┘
         │                  │                  │
   ┌─────▼──────┐    ┌──────▼──────┐   ┌──────▼──────┐
   │  Agent 1   │    │  Agent 2    │   │  Agent 3    │
   │ extractor  │───>│  writer     │──>│  reviewer   │
   │            │    │             │   │             │
   │ PDF内容提取 │    │ Markdown撰写│   │ 排版审核     │
   └────────────┘    └─────────────┘   └─────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
   content.json       article.md          final.html
   figures/           (Markdown)          (可直接粘贴)
```

## Agent 职责

### Agent 1: extractor（PDF内容提取器）
- **文件**：`extractor.md`
- **输入**：PDF 文件路径
- **输出**：`.claude/tmp/extracted/` 下的结构化 JSON + 图片
- **工具**：`extract_content.py`（统一编排）、`extract_figures.py`（PyMuPDF）、pdfplumber、`validate_run.py`
- **提取内容**：论文元信息、章节文本、Figures（>200x200px）、Figure Legends、关键数据
- **状态文件**：`run_state.json` 记录输入 PDF、输出产物、图片数量和确定性校验结果

### Agent 2: writer（科普文章撰写器）
- **文件**：`writer.md`
- **输入**：extractor 输出的结构化内容 + 用户选择的风格类型
- **输出**：Markdown 文件（`.claude/tmp/extracted/article.md`）
- **参考**：`writing-techniques.md`（写作技巧）、`company-footer.md`（企业引流）
- **格式**：标准 Markdown，图片 `![描述](figures/fig1.png)`，图注 `**Fig. 1** 说明`

### Agent 3: reviewer（排版审核器）
- **文件**：`reviewer.md`
- **输入**：渲染后的 HTML 文件
- **输出**：审核通过的最终 HTML + 审核报告
- **参考**：`article-checklist.md`（质检清单）
- **检查项**：图片完整性、图文引用一致性、微信兼容性、排版质量、内容质量、商业闭环

## 数据流

```
PDF文件
  → extractor → content.json + full_text.txt + figure_map.json + run_state.json + figures/
  → writer → article.md (Markdown)
  → md2wechat.py → draft.html (带内联样式)
  → reviewer → final.html (可直接粘贴到微信编辑器)
```

## 使用方式

在 Claude Code 中执行：
```
/paper2wechat path/to/paper.pdf
```
