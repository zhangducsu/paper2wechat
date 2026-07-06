PDF论文转微信公众号科普文章 - 多Agent工作组

用户提供的PDF论文路径：$ARGUMENTS

## 工作流程

请严格按照以下步骤执行，每一步完成后进入下一步：

---

### 第零步：P0 环境基线检查

正式处理 PDF 前必须先检查运行环境：

```bash
# Windows PowerShell 推荐
powershell -ExecutionPolicy Bypass -File .claude/scripts/doctor.ps1

# 其他环境
python .claude/scripts/check_env.py --json-output .claude/tmp/env_status.json
```

要求：
1. `env_status.json` 或终端 JSON 输出中的 `status` 必须为 `pass`
2. Python 必须是可执行解释器，不能是 WindowsApps 0 字节占位别名
3. `PyMuPDF`、`pdfplumber`、`markdown`、`beautifulsoup4` 必须可导入
4. `.claude/tmp/` 与 `output/` 必须可写

若检查失败，停止工作流并向用户报告失败项。

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
1. 优先使用确定性抽取脚本，一次性生成文本、图片、figure map、content schema 与运行状态：
   ```bash
   python .claude/scripts/extract_content.py "$ARGUMENTS" --output-dir .claude/tmp/extracted
   ```
2. 确认以下文件存在：
   - `.claude/tmp/extracted/content.json`
   - `.claude/tmp/extracted/full_text.txt`
   - `.claude/tmp/extracted/figures/figure_map.json`
   - `.claude/tmp/extracted/validation.json`
   - `.claude/tmp/extracted/run_state.json`
3. `run_state.json` 与 `validation.json` 中的 `status` 必须为 `pass`，否则停止工作流并报告失败项。

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
7. 同步全局素材并规范 Markdown 图片路径：
   ```bash
   python .claude/scripts/sync_assets.py \
     --figures-dir .claude/tmp/extracted/figures \
     --article .claude/tmp/extracted/article.md
   python .claude/scripts/sync_assets.py \
     --figures-dir output/figures
   ```

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
  --theme-logo .claude/templates/references/global_assets/logo.jpg \
  --palette-output output/theme_palette.json

# 使用自定义模板
python3 .claude/scripts/md2wechat.py .claude/tmp/extracted/article.md \
  --output output/文章标题.html \
  --template .claude/templates/themes/custom_20250510.css \
  --theme-logo .claude/templates/references/global_assets/logo.jpg \
  --palette-output output/theme_palette.json
```

同时将图片复制到输出目录：
```bash
cp .claude/tmp/extracted/figures/* output/figures/
```

---

### 第七步：生成微信公众号封面图

先使用 AI 生图功能生成封面背景图，要求画面无文字、无 Logo、无 AI 生图水印，并保存为：

```text
output/ai_cover_background.png
```

再使用 `scripts/generate_cover.py` 本地叠加文章标题和公司 Logo 水印：

```bash
python .claude/scripts/generate_cover.py \
  --article output/文章标题.md \
  --figures-dir output/figures \
  --background output/ai_cover_background.png \
  --background-source ai_generated \
  --require-ai-background \
  --logo .claude/templates/references/global_assets/logo.jpg \
  --theme-logo .claude/templates/references/global_assets/logo.jpg \
  --palette-output output/cover_theme_palette.json \
  --output output/文章标题_cover.png \
  --square-output output/文章标题_cover_square.png \
  --json-output output/cover_report.json
```

要求：
1. 封面背景必须由 AI 生图功能生成，不能用文章首图或本地渐变图冒充
2. 封面图尺寸为 `900x383`
3. 同时生成中心安全区方图 `383x383`
4. 使用公司 Logo 作为半透明水印
5. 推文和封面主题色必须来自公司 Logo，生成 `theme_palette.json`
6. 如果 Logo 含多种颜色，以主色为中心生成匹配的和谐色系
7. `cover_report.json` 中 `background_source` 必须为 `ai_generated`
8. `cover_report.json` 中 `ai_generated_background` 必须为 `true`
9. `cover_report.json` 中 `ai_watermark` 必须为 `false`，`logo_watermark_applied` 必须为 `true`

---

### 第八步：Agent 3 - 排版审核

**角色**：参考 `agents/reviewer.md` 中的系统提示

执行以下操作：
1. 读取 `output/文章标题.html`
2. 按审核清单逐项检查（图片完整性、图文引用、微信兼容性、排版质量、内容质量）
3. **静默读取 `templates/references/article-checklist.md`，执行风格类型专属质检**
4. **执行商业闭环检查**（引流矩阵、顺滑过渡、转化组件）
5. 使用确定性校验脚本复核图片引用与微信兼容性：
   ```bash
   python .claude/scripts/validate_run.py \
     --content .claude/tmp/extracted/content.json \
     --base-dir .claude/tmp/extracted \
     --article output/文章标题.md \
     --html output/文章标题.html \
     --output-dir output \
     --cover output/文章标题_cover.png \
     --cover-report output/cover_report.json \
     --require-ai-cover \
     --json-output output/validation.json
   ```
6. 修复发现的所有问题，直到 `output/validation.json` 中 `status` 为 `pass`

---

### 第九步：输出最终结果

1. 在 `output/` 下生成：
   - `文章标题.html`（最终可直接粘贴的HTML）
   - `文章标题_cover.png`（微信公众号封面图，900x383）
   - `文章标题_cover_square.png`（中心安全区方图，383x383）
   - `ai_cover_background.png`（AI 生图封面背景）
   - `theme_palette.json`（从公司 Logo 提取的推文主题色和和谐色系）
   - `figures/` 目录（所有论文图片）
   - `文章标题.md`（Markdown源文件，方便后续修改）
   - `cover_report.json`（封面生成报告）
   - `validation.json`（最终确定性校验报告）
   
2. 向用户报告：
   - 文章标题
   - 选择的风格类型
   - 选择的排版主题
   - 使用了哪些Figures
   - 封面图路径、AI 背景图路径、是否添加 Logo 水印、是否无 AI 生图水印
   - 审核结果（通过/修复项）
   - 确定性校验结果（`validation.json` 状态）
   - 文件路径

---

## 注意事项

- 如果PDF是扫描版（提取文本为空），提示用户并建议OCR处理
- 图片提取失败时，跳过该图片并记录警告
- 企业引流信息从 `templates/references/company-footer.md` 读取
- 最终HTML必须可以直接 Ctrl+A → Ctrl+C → 粘贴到微信公众号编辑器
- **必须向用户确认风格类型后才开始撰写**
- **必须向用户确认排版主题后才开始渲染**
