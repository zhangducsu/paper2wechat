拆解竞品推文 - 学习优化工作流

用户输入：$ARGUMENTS

## 任务

对目标推文进行"结构模式"、"写作技巧"、"商业转化埋点"三维硬核拆解，并将有价值的新模式/新技巧持久化沉淀到知识库中。

---

## 第一步：获取推文内容

根据用户输入判断内容来源：

### 情况A：用户直接粘贴了HTML内容
直接读取，跳到第二步。

### 情况B：用户提供了微信推文链接

按以下顺序尝试获取：

1. **首选：调用 wechat-parser MCP 工具**（如果已配置）
   - 使用 `parse_wechat_article` 工具，参数：`{"url": "链接", "format": "json", "extract_method": "auto"}`
   - 如果返回 `success: true`，提取内容，跳到第二步

2. **备选：尝试浏览器抓取**

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

---

## 第二步：三维硬核拆解

读取推文内容后，按以下三个维度进行深度拆解：

### 维度一：结构模式分析

1. **文章类型判断**：属于哪种风格类型？
   - 类型一（叙事转化风）：引子痛点 → 核心突破 → 落地场景 → 行业意义 → 商业承接
   - 类型二（标准八股风）：引言导读 → 档案库 → 核心小结 → 研究方法 → 结果图形 → 结论启示 → 技术推介
   - 其他/混合类型

2. **章节编排**：共几个大章节？篇幅比例？过渡方式？信息密度分布？

3. **标题体系**：大标题格式？小标题格式？层级区分方式？

4. **起承转合节奏**：开头抓注意力方式？中间维持兴趣？结尾收束引导转化？

### 维度二：写作技巧分析

1. **学术通俗化策略**：比喻使用？术语处理？通俗化程度？

2. **数据呈现方式**：核心数据突出方式？对比数据？上下文铺垫？

3. **语言风格特征**：人称？情感色彩？句式特点？

4. **视觉排版技巧**：特殊排版元素？图文穿插节奏？重点视觉强化？

### 维度三：商业转化埋点分析

1. **引流矩阵**：相关阅读超链接？历史文章交叉引用？锚文本设计？

2. **服务承接方式**：科普→商业过渡自然度？技术服务推介位置？技术映射紧密度？

3. **转化组件设计**：转化组件类型？视觉设计？行动号召（CTA）？

---

## 第三步：归类与建档

静默读取知识库文件：
- `templates/references/structure-patterns.md`
- `templates/references/writing-techniques.md`
- `templates/references/article-checklist.md`

判断归类：
- **匹配现有类型** → 归入该类型
- **风格独特** → 向用户提议建立【新类型】

输出拆解报告，请用户确认。

---

## 第四步：持久化沉淀（Critical）

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

## 第五步：输出结果

向用户报告：
- 拆解报告摘要
- 知识库更新内容（新增/跳过条目）
- 当前知识库的类型总数
