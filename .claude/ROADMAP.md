# paper2wechat 后续版本规划

## 当前版本 v1.5 状态

**已实现功能**：
- 3个Agent（extractor → writer → reviewer）
- 3个斜杠命令（/paper2wechat、/extract-style、/analyze-article）
- Markdown→HTML渲染器（md2wechat.py）
- 知识库进化机制（只追加不覆盖）
- wechat-parser-mcp集成
- doocs主题 + 自定义模板支持

**已知遗留问题**：
1. `md2wechat.py` 列表闭合启发式判断脆弱（嵌套列表可能出错）
2. `md2wechat.py` 表格表头/表体区分启发式（非标准表格可能误判）
3. `extract_figures.py` 同页多图编号可能错位
4. `custom_yijiyin_20250510_inline.json` 未被渲染器读取（仅作参考）

---

## v1.6 — 稳定性修复

### 目标
修复已知遗留问题，提升渲染稳定性

### 具体改动

| 文件 | 改动内容 |
|------|----------|
| `scripts/md2wechat.py` | 重写列表处理为状态机模式，支持嵌套列表 |
| `scripts/md2wechat.py` | 改进表格解析，检测 `\|:--\|` 对齐标记区分表头 |
| `scripts/extract_figures.py` | 优化Figure编号匹配，优先匹配图片附近的Figure caption |
| `scripts/md2wechat.py` | 实现 JSON 模板加载逻辑，读取 `_inline.json` 文件 |

---

## v1.7 — 功能增强

### 目标
扩展Markdown语法支持，提升文章表现力

### 具体改动

| 文件 | 改动内容 |
|------|----------|
| `scripts/md2wechat.py` | 支持数学公式：`$...$` 行内公式、`$$...$$` 块级公式（转换为图片或Unicode） |
| `scripts/md2wechat.py` | 支持脚注：`[^1]` 和 `[^1]: ...` 语法 |
| `scripts/md2wechat.py` | 支持任务列表：`- [ ]` 和 `- [x]` |
| `scripts/md2wechat.py` | 支持高亮标记：`==高亮文字==` |
| `agents/writer.md` | 更新Markdown格式规范，说明新支持的语法 |
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

## v1.9 — 质量保障

### 目标
建立测试体系，确保代码质量

### 具体改动

| 文件 | 改动内容 |
|------|----------|
| `tests/test_md2wechat.py` | 新建单元测试：Markdown→HTML转换 |
| `tests/test_extract_figures.py` | 新建单元测试：PDF图片提取 |
| `tests/fixtures/` | 新建测试数据：样例PDF、样例Markdown |
| `.github/workflows/test.yml` | 新建CI流程：自动运行测试 |
| `scripts/md2wechat.py` | 添加类型注解 |
| `scripts/extract_figures.py` | 添加类型注解 |

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
