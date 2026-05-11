PDF论文转微信公众号科普文章 - 多Agent工作组

用户提供的PDF论文路径：$ARGUMENTS

## 工作流程

请严格按照以下步骤执行，每一步完成后进入下一步：

---

### 第一步：初始化工作目录

创建临时工作目录：
```bash
mkdir -p .claude/tmp/extracted/figures output/figures
```

---

### 第二步：Agent 1 - PDF内容提取

**角色**：参考 `agents/extractor.md` 中的系统提示

执行以下操作：
1. 使用 `scripts/extract_figures.py` 将PDF图片提取到 `.claude/tmp/extracted/figures/`
2. 使用 `pdfplumber` 提取全文文本，按章节结构化
3. 提取论文元信息（标题、作者、期刊、年份、DOI）
4. 将提取的结构化内容保存为 `.claude/tmp/extracted/content.json`

---

### 第三步：动态定调（Critical）

**必须执行此步骤，向用户确认文章风格类型！**

1. 静默读取 `templates/references/structure-patterns.md` 的目录树
2. 向用户列出可用类型并询问选型：
   - **类型一：叙事转化风**（面向临床医生、非生信专业研究者，主打痛点共鸣与转化）
   - **类型二：标准八股风**（面向有明确生信外包需求的科研同行，主打严谨专业）
3. 确定类型后，静默读取 `templates/references/writing-techniques.md` 中对应风格的技巧
4. 输出文章大纲待用户确认

---

### 第四步：Agent 2 - 科普文章撰写（Markdown格式）

**角色**：参考 `agents/writer.md` 中的系统提示

执行以下操作：
1. 读取 `.claude/tmp/extracted/content.json` 获取结构化内容
2. 读取 `templates/references/writing-techniques.md` 获取写作技巧
3. 根据用户选择的风格类型，按对应结构撰写**Markdown格式**文章
4. 将图片从 `.claude/tmp/extracted/figures/` 复制到 `output/figures/`
5. **静默读取 `templates/references/company-footer.md`，将其追加到文章末尾**
6. 保存Markdown文件到 `.claude/tmp/extracted/article.md`

**重要**：输出Markdown格式，不要输出HTML！

---

### 第五步：选择排版主题

向用户询问排版主题：

```
请选择排版主题：
1. doocs/default（经典风格）
2. doocs/grace（优雅风格）
3. doocs/simple（简洁风格）
4. 自定义模板（从 templates/themes/ 中选择）
```

---

### 第六步：Markdown → HTML渲染

使用 `scripts/md2wechat.py` 将Markdown转换为带排版的HTML：

```bash
# 使用doocs主题
python3 .claude/scripts/md2wechat.py .claude/tmp/extracted/article.md \
  --output output/文章标题.html \
  --theme default \
  --primary-color "#20B2AA"

# 使用自定义模板
python3 .claude/scripts/md2wechat.py .claude/tmp/extracted/article.md \
  --output output/文章标题.html \
  --template .claude/templates/themes/custom_20250510.css \
  --primary-color "#20B2AA"
```

同时将图片复制到输出目录：
```bash
cp .claude/tmp/extracted/figures/* output/figures/
```

---

### 第七步：Agent 3 - 排版审核

**角色**：参考 `agents/reviewer.md` 中的系统提示

执行以下操作：
1. 读取 `output/文章标题.html`
2. 按审核清单逐项检查（图片完整性、图文引用、微信兼容性、排版质量、内容质量）
3. **静默读取 `templates/references/article-checklist.md`，执行风格类型专属质检**
4. **执行商业闭环检查**（引流矩阵、顺滑过渡、转化组件）
5. 修复发现的所有问题

---

### 第八步：输出最终结果

1. 在 `output/` 下生成：
   - `文章标题.html`（最终可直接粘贴的HTML）
   - `figures/` 目录（所有论文图片）
   - `文章标题.md`（Markdown源文件，方便后续修改）
   
2. 向用户报告：
   - 文章标题
   - 选择的风格类型
   - 选择的排版主题
   - 使用了哪些Figures
   - 审核结果（通过/修复项）
   - 文件路径

---

## 注意事项

- 如果PDF是扫描版（提取文本为空），提示用户并建议OCR处理
- 图片提取失败时，跳过该图片并记录警告
- 企业引流信息从 `templates/references/company-footer.md` 读取
- 最终HTML必须可以直接 Ctrl+A → Ctrl+C → 粘贴到微信公众号编辑器
- **必须向用户确认风格类型后才开始撰写**
- **必须向用户确认排版主题后才开始渲染**
