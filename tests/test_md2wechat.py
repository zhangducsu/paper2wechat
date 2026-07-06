import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from md2wechat import convert_md_to_html, load_inline_template, load_styles, merge_style_maps, render_markdown_file  # noqa: E402


class Md2WechatTest(unittest.TestCase):
    def test_escapes_raw_html_and_applies_inline_styles(self):
        html = convert_md_to_html("正文 <script>alert(1)</script> **重点**", load_styles())

        self.assertNotIn("<script", html.lower())
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("<strong", html)
        self.assertIn("style=", html)

    def test_supports_nested_lists_tables_and_code_blocks(self):
        md = """# 标题

- 一级
  - 二级
- 另一个

| A | B |
|---|---|
| 1 | 2 |

```python
if True:
    value = 1
```
"""
        html = convert_md_to_html(md, load_styles())

        self.assertIn("<ul", html)
        self.assertGreaterEqual(html.count("<ul"), 2)
        self.assertIn("<table", html)
        self.assertIn("<th", html)
        self.assertIn("<td", html)
        self.assertIn("<pre", html)
        self.assertIn("    value = 1", html)

    def test_loads_inline_json_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "inline.json"
            template.write_text(
                json.dumps({"styles": {"h2": "color:red; position:absolute;", "container": "padding:8px;"}}),
                encoding="utf-8",
            )

            styles = load_inline_template(template)

            self.assertEqual(styles["h2"], "color:red")
            self.assertEqual(styles["section"], "padding:8px")

            merged = merge_style_maps({"h2": "font-weight:bold;"}, styles)
            self.assertIn("font-weight:bold", merged["h2"])
            self.assertIn("color:red", merged["h2"])
            self.assertNotIn("position", merged["h2"])

    def test_render_file_uses_sibling_inline_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            md = base / "article.md"
            css = base / "custom.css"
            inline = base / "custom_inline.json"
            output = base / "article.html"
            md.write_text("## 小标题\n", encoding="utf-8")
            css.write_text("h2 { color: blue; }", encoding="utf-8")
            inline.write_text(json.dumps({"styles": {"h2": "color:red;"}}), encoding="utf-8")

            render_markdown_file(md, output, "default", str(css), None, "#20B2AA")

            html = output.read_text(encoding="utf-8")
            self.assertIn("color:red", html)
            self.assertNotIn("<style", html.lower())
            self.assertNotIn(" class=", html.lower())

    def test_supports_p4_enhanced_markdown_features(self):
        md = """## 增强语法

- [x] 已完成
- [ ] 未完成

这是一段 ==高亮文字==，包含行内公式 $AUC = TP/(TP+FN)$。

$$
TH + cGAS = STING
$$

脚注引用[^1]。

[^1]: 这是脚注内容。
"""
        html = convert_md_to_html(md, load_styles())

        self.assertIn("☑", html)
        self.assertIn("☐", html)
        self.assertIn("<mark", html)
        self.assertIn("高亮文字", html)
        self.assertIn("AUC = TP/(TP+FN)", html)
        self.assertIn("TH + cGAS = STING", html)
        self.assertIn("脚注内容", html)
        self.assertIn("href=", html)
        self.assertNotIn(" class=", html.lower())


if __name__ == "__main__":
    unittest.main()
