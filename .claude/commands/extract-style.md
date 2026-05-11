从微信公众号推文提取样式模板 + 写作技巧拆解

用户输入：$ARGUMENTS

## 任务

从用户提供的微信公众号推文中**同时完成两件事**：
1. 提取排版样式，保存为可复用的模板文件
2. 拆解写作技巧，沉淀到知识库

---

## 第一步：获取推文内容

根据用户输入判断内容来源：

### 情况A：用户直接粘贴了HTML内容
直接读取HTML内容，跳到第二步。

### 情况B：用户提供了微信推文链接

按以下顺序尝试获取：

1. **首选：调用 wechat-parser MCP 工具**（如果已配置）
   - 使用 `parse_wechat_article` 工具，参数：`{"url": "链接", "format": "json", "detail": "detailed", "extract_method": "auto"}`
   - **⚠️ 必须传 `"detail": "detailed"`**，否则 concise 模式会截断正文，丢失排版样式细节
   - 如果返回 `success: true`，提取 `content` 字段中的HTML内容，跳到第二步

2. **备选：尝试浏览器抓取**
   - 导航到推文链接，尝试获取正文

3. **如果以上均失败**：
   > ⚠️ 自动获取失败。请使用以下任一方式：
   >
   > **方式一：部署 wechat-parser-mcp（推荐，一劳永逸）**
   > 详见 `部署指南.md` 第四章步骤4
   >
   > **方式二：浏览器书签（快速备用）**
   > 1. 在浏览器中新建书签（Ctrl+D）
   > 2. 编辑书签，将"网址"替换为：
   > ```
   > javascript:void(function(){var c=document.getElementById('js_content');if(!c){alert('未找到正文区域');return}var h=c.outerHTML;navigator.clipboard.writeText(h).then(function(){alert('✅ 已复制！回到Claude Code粘贴即可。')}).catch(function(){var ta=document.createElement('textarea');ta.value=h;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);alert('✅ 已复制！回到Claude Code粘贴即可。')})})();
   > ```
   > 3. 打开推文 → 点击书签 → 回来Ctrl+V粘贴

4. 等待用户粘贴HTML内容

### 情况C：用户提供了本地HTML文件路径
直接读取文件内容。

---

## 第二步：提取排版样式

从HTML中提取以下元素的 `style` 属性：

| 元素 | 提取内容 |
|------|----------|
| 一级标题 h1 | font-size, color, text-align, border, margin, padding |
| 二级标题 h2 | font-size, color, background, margin, padding |
| 三级标题 h3 | font-size, color, border-left, margin, padding |
| 段落 p | font-size, color, line-height, letter-spacing, margin |
| 引用块 blockquote | border-left, background, padding, border-radius |
| 图片 img | border-radius, margin, max-width |
| 加粗 strong | color, font-weight |
| 链接 a | color, text-decoration |
| 表格 table/th/td | border, padding, background |
| 信息框/卡片 | background, border, border-radius, padding |

生成两个文件，保存到 `.claude/templates/themes/`：
- `custom_YYYYMMDD.css` — CSS格式模板
- `custom_YYYYMMDD_inline.json` — 内联样式映射（供md2wechat.py使用）

---

## 第三步：三维硬核拆解

对推文内容进行三个维度的深度拆解：

**维度一：结构模式**
- 文章类型判断（叙事转化风 / 标准八股风 / 其他）
- 章节编排、信息密度分布
- 标题体系、起承转合节奏

**维度二：写作技巧**
- 学术通俗化策略（比喻、术语处理）
- 数据呈现方式（加粗、独立行、信息卡片）
- 语言风格特征（人称、情感、句式）
- 视觉排版技巧

**维度三：商业转化埋点**
- 引流矩阵（相关阅读、交叉引用）
- 服务承接方式（过渡自然度）
- 转化组件设计（CTA、联系方式）

---

## 第四步：归类与建档

静默读取知识库文件：
- `templates/references/structure-patterns.md`
- `templates/references/writing-techniques.md`
- `templates/references/article-checklist.md`

判断归类：
- **匹配现有类型** → 归入该类型
- **风格独特** → 向用户提议建立【新类型】

输出拆解报告，请用户确认。

---

## 第五步：持久化沉淀（Critical）

用户确认后，严格执行**"只追加(Append)不覆盖(Overwrite)"**原则，更新以下三个知识库文件：

### 必须更新的三个文件

| 文件 | 更新内容 | 追加位置 |
|------|----------|----------|
| `templates/references/structure-patterns.md` | 新结构模式、章节编排方式 | 对应类型标题下 |
| `templates/references/writing-techniques.md` | 新写作技巧、语言风格特征 | 对应类型技巧列表末尾 |
| `templates/references/article-checklist.md` | 新质检维度、商业转化检查点 | 对应类型质检维度下 |

### 更新规则

- **新技巧** → 追加到 `writing-techniques.md` 对应类型末尾（自动去重）
- **新结构模式** → 追加到 `structure-patterns.md` 对应类型下
- **新质检维度** → 追加到 `article-checklist.md` 对应类型下
- **全新类型** → **必须在所有三个文件中同步创建**新的 `## 类型X` 层级标题，保持三个文件的结构一致性

> ⚠️ **重要**：不能只更新一个文件！三个知识库文件必须保持同步更新，否则 `writer` Agent 在读取时会出现信息不一致。

---

## 第六步：输出结果

向用户报告：
- 样式模板文件路径
- 拆解报告摘要
- 知识库更新内容（新增/跳过条目）
- 如何使用：`/paper2wechat` 选"自定义模板"即可使用新样式
