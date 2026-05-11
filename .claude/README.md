# PDF论文 → 微信公众号文章 Agent工作组

基于 Claude Code 多 Agent 架构的学术论文科普文章自动化生成工具。

## 快速开始

### 1. 安装依赖

```bash
pip install PyMuPDF pdfplumber
```

### 2. 使用

在 Claude Code 中执行：

```
/paper2wechat path/to/your/paper.pdf
```

工作流自动完成：提取PDF → 确认风格 → 撰写Markdown → 选主题 → 渲染HTML → 审核 → 输出

### 3. 发布到微信公众号

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
├── scripts/           # Python/JS脚本（3个）
├── templates/         # 知识库 + 排版主题
│   ├── references/    # 写作技巧、结构模板、质检清单、企业信息
│   └── themes/        # doocs主题 + 自定义模板
└── 部署指南.md        # 完整部署文档
```

## 详细文档

完整的部署步骤、配置说明、自定义方法和常见问题，请查看 [部署指南.md](./部署指南.md)。
