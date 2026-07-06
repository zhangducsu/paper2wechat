#!/usr/bin/env python3
"""
Markdown → 微信公众号 HTML 转换器。

P2 基线：
- 使用 Python-Markdown 解析 Markdown，不再手写列表/表格状态机；
- 使用 BeautifulSoup 给允许的 HTML 标签写入内联样式；
- 默认转义原始 HTML 标签，避免 Markdown 中的 HTML 直通到最终稿；
- 支持 CSS 主题和 `_inline.json` 内联样式模板。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    import markdown
    from bs4 import BeautifulSoup
    from bs4.element import NavigableString, Tag
except ImportError as exc:  # pragma: no cover - 环境检查会覆盖，这里给 CLI 友好报错
    print(f"缺少依赖: {exc}. 请先运行 pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(1)


DEFAULT_VARS = {
    "--md-font-family": "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Microsoft YaHei', sans-serif",
    "--md-font-size": "15px",
    "--md-primary-color": "#20B2AA",
    "--foreground": "0 0% 0%",
    "--blockquote-background": "rgba(0,0,0,0.03)",
}

DEFAULT_STYLES = {
    "section": "padding:16px; max-width:100%; box-sizing:border-box;",
    "h1": "padding:0 1em; border-bottom:2px solid {primary}; margin:2em auto 1em; color:#111; font-size:18px; font-weight:bold; text-align:center;",
    "h2": "padding:0.2em 0.5em; margin:2.5em auto 1.2em; color:#fff; background:{primary}; font-size:18px; font-weight:bold; text-align:center; border-radius:4px;",
    "h3": "padding-left:8px; border-left:3px solid {primary}; margin:2em 8px 0.75em 0; color:#111; font-size:16px; font-weight:bold; line-height:1.3;",
    "h4": "margin:2em 8px 0.5em; color:{primary}; font-size:15px; font-weight:bold;",
    "h5": "margin:1.5em 8px 0.5em; color:{primary}; font-size:15px; font-weight:bold;",
    "h6": "margin:1.5em 8px 0.5em; color:{primary}; font-size:15px; font-weight:bold;",
    "p": "margin:1.5em 8px; letter-spacing:0.05em; color:#333; line-height:1.75;",
    "blockquote": "font-style:normal; padding:1em; border-left:4px solid {primary}; border-radius:6px; color:#333; background:rgba(0,0,0,0.03); margin:1em 8px;",
    "ul": "list-style-type:disc; padding-left:1.4em; margin:1em 8px; line-height:1.75;",
    "ol": "padding-left:1.4em; margin:1em 8px; line-height:1.75;",
    "li": "margin:0.35em 0;",
    "strong": "color:{primary}; font-weight:bold;",
    "em": "font-style:italic;",
    "a": "color:#576b95; text-decoration:none;",
    "img": "display:block; max-width:100%; margin:0.1em auto 0.5em; border-radius:4px; box-shadow:0 2px 12px rgba(0,0,0,0.12);",
    "table": "border-collapse:collapse; margin:1.5em 8px; width:100%; max-width:100%;",
    "thead": "",
    "tbody": "",
    "tr": "",
    "th": "border:1px solid #dfdfdf; padding:0.35em 0.6em; font-weight:bold; background:rgba(0,0,0,0.05); text-align:center;",
    "td": "border:1px solid #dfdfdf; padding:0.35em 0.6em; text-align:left;",
    "hr": "border-style:solid; border-width:2px 0 0; border-color:rgba(0,0,0,0.1); height:0.4em; margin:1.5em 0;",
    "pre": "font-size:90%; overflow-x:auto; border-radius:8px; padding:0.75em 1em; background:#f6f8fa; margin:1em 8px; white-space:pre-wrap;",
    "code": "font-size:90%; color:#d14; background:rgba(27,31,35,0.05); padding:3px 5px; border-radius:4px;",
    "code_block": "font-size:90%; color:#d14; background:none; white-space:pre-wrap;",
    "mark": "background:rgba(255,235,59,0.45); color:#111; padding:0 0.2em; border-radius:2px;",
    "math_inline": "font-family:Menlo,Consolas,monospace; color:{primary}; background:rgba(0,0,0,0.04); padding:0.05em 0.35em; border-radius:4px;",
    "math_block": "display:block; font-family:Menlo,Consolas,monospace; color:{primary}; background:rgba(0,0,0,0.04); padding:0.75em 1em; margin:1em 8px; border-radius:6px; overflow-x:auto; white-space:pre-wrap;",
    "sup": "font-size:0.75em; line-height:0; vertical-align:super;",
    "div": "margin:1em 8px;",
}

ALLOWED_ATTRS = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
}

DISALLOWED_STYLE_KEYS = {
    "-webkit-line-clamp",
    "animation",
    "background-image",
    "filter",
    "float",
    "position",
    "transform",
    "transition",
    "z-index",
}


def resolve_css_vars(css_text: str, variables: Optional[Dict[str, str]] = None) -> str:
    values = dict(DEFAULT_VARS)
    if variables:
        values.update(variables)

    def replace_hsl_var(match: re.Match) -> str:
        value = values.get(match.group(1), "0 0% 0%")
        return f"hsl({value})"

    def replace_var(match: re.Match) -> str:
        return values.get(match.group(1), match.group(0))

    css_text = re.sub(r"hsl\(var\((--[^)]+)\)\)", replace_hsl_var, css_text)
    css_text = re.sub(r"var\((--[^)]+)\)", replace_var, css_text)
    css_text = re.sub(
        r"calc\(\s*([0-9.]+)px\s*\*\s*([0-9.]+)\s*\)",
        lambda m: f"{float(m.group(1)) * float(m.group(2)):.2f}px",
        css_text,
    )
    return css_text


def parse_style(style: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for declaration in style.split(";"):
        if ":" not in declaration:
            continue
        key, value = declaration.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if not key or not value or key in DISALLOWED_STYLE_KEYS or key.startswith("-webkit-"):
            continue
        parsed[key] = value
    return parsed


def style_dict_to_text(style: Dict[str, str]) -> str:
    return "; ".join(f"{key}:{value}" for key, value in style.items() if value)


def merge_styles(*styles: str) -> str:
    merged: Dict[str, str] = {}
    for style in styles:
        merged.update(parse_style(style))
    return style_dict_to_text(merged)


def merge_style_maps(base: Dict[str, str], overlay: Dict[str, str]) -> Dict[str, str]:
    result = dict(base)
    for tag, style in overlay.items():
        result[tag] = merge_styles(result.get(tag, ""), style)
    return result


def tag_from_selector(selector: str) -> Optional[str]:
    selector = selector.strip()
    if not selector:
        return None
    if any(token in selector for token in ["#", ".", "[", ":", "+", "~"]):
        return None
    first = re.split(r"\s+|>", selector, maxsplit=1)[0].strip()
    if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9]*", first):
        return first.lower()
    return None


def parse_css_to_inline_styles(css_text: str, primary_color: Optional[str] = None) -> Dict[str, str]:
    variables = {"--md-primary-color": primary_color} if primary_color else None
    css_text = resolve_css_vars(css_text, variables)
    css_text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.S)

    styles_map: Dict[str, str] = {}
    for match in re.finditer(r"([^{}]+)\{([^{}]+)\}", css_text, flags=re.S):
        selectors = [selector.strip() for selector in match.group(1).split(",")]
        style = style_dict_to_text(parse_style(match.group(2)))
        if not style:
            continue
        for selector in selectors:
            tag = tag_from_selector(selector)
            if not tag:
                continue
            styles_map[tag] = merge_styles(styles_map.get(tag, ""), style)
    return styles_map


def load_inline_template(path: Path) -> Dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    styles = data.get("styles", data)
    if not isinstance(styles, dict):
        raise ValueError(f"inline 模板格式错误: {path}")

    result: Dict[str, str] = {}
    for key, value in styles.items():
        if not isinstance(value, str):
            continue
        tag = "section" if key == "container" else key
        result[tag] = style_dict_to_text(parse_style(value))
    return result


def sibling_inline_template(css_path: Path) -> Optional[Path]:
    stem = css_path.stem
    candidates = []
    if stem.endswith("_inline"):
        candidates.append(css_path)
    else:
        candidates.append(css_path.with_name(f"{stem}_inline.json"))
        candidates.append(css_path.with_suffix(".json"))
    for candidate in candidates:
        if candidate.exists() and candidate.suffix.lower() == ".json":
            return candidate
    return None


def default_styles(primary_color: str) -> Dict[str, str]:
    return {
        tag: style.format(primary=primary_color)
        for tag, style in DEFAULT_STYLES.items()
    }


def load_styles(
    theme: str = "default",
    template: Optional[str] = None,
    inline_template: Optional[str] = None,
    primary_color: str = "#20B2AA",
) -> Dict[str, str]:
    styles = default_styles(primary_color)

    theme_dir = Path(__file__).resolve().parent.parent / "templates" / "themes"
    if template:
        css_path = Path(template)
        css_text = css_path.read_text(encoding="utf-8")
        styles = merge_style_maps(styles, parse_css_to_inline_styles(css_text, primary_color))
        auto_inline = sibling_inline_template(css_path)
        if auto_inline:
            styles = merge_style_maps(styles, load_inline_template(auto_inline))
    else:
        css_text = ""
        base_path = theme_dir / "doocs_base.css"
        theme_path = theme_dir / f"doocs_{theme}.css"
        if base_path.exists():
            css_text += base_path.read_text(encoding="utf-8") + "\n"
        css_text += theme_path.read_text(encoding="utf-8")
        styles = merge_style_maps(styles, parse_css_to_inline_styles(css_text, primary_color))

    if inline_template:
        styles = merge_style_maps(styles, load_inline_template(Path(inline_template)))

    styles["strong"] = merge_styles(styles.get("strong", ""), f"color:{primary_color}; font-weight:bold;")
    return styles


def escape_raw_html(md_text: str) -> str:
    def replace(match: re.Match) -> str:
        token = match.group(0)
        return token.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    return re.sub(r"</?[A-Za-z][^>\n]*>|<!--.*?-->", replace, md_text, flags=re.S)


def normalize_list_indentation(md_text: str) -> str:
    normalized: List[str] = []
    for line in md_text.splitlines():
        match = re.match(r"^( +)((?:[-*+])|(?:\d+\.))\s+", line)
        if match:
            leading = len(match.group(1))
            if leading % 4 != 0 and leading % 2 == 0:
                line = (" " * ((leading // 2) * 4)) + line[leading:]
        normalized.append(line)
    return "\n".join(normalized)


def normalize_task_lists(md_text: str) -> str:
    def replace(match: re.Match) -> str:
        prefix = match.group(1)
        checked = match.group(2).lower() == "x"
        symbol = "☑" if checked else "☐"
        return f"{prefix}{symbol} "

    return re.sub(r"^(\s*[-*+]\s+)\[([ xX])\]\s+", replace, md_text, flags=re.M)


def extract_math_tokens(md_text: str) -> Tuple[str, Dict[str, Dict[str, str]]]:
    tokens: Dict[str, Dict[str, str]] = {}

    def replace_block(match: re.Match) -> str:
        token = f"@@P2W_MATH_BLOCK_{len(tokens)}@@"
        tokens[token] = {"type": "math_block", "value": match.group(1).strip()}
        return f"\n\n{token}\n\n"

    def replace_inline(match: re.Match) -> str:
        token = f"@@P2W_MATH_INLINE_{len(tokens)}@@"
        tokens[token] = {"type": "math_inline", "value": match.group(1).strip()}
        return token

    md_text = re.sub(r"\$\$\s*([\s\S]+?)\s*\$\$", replace_block, md_text)
    md_text = re.sub(r"(?<!\$)\$([^$\n]+?)\$(?!\$)", replace_inline, md_text)
    return md_text, tokens


def prepare_markdown(md_text: str) -> Tuple[str, Dict[str, Dict[str, str]]]:
    md_text = normalize_task_lists(md_text)
    md_text, math_tokens = extract_math_tokens(md_text)
    md_text = normalize_list_indentation(md_text)
    return escape_raw_html(md_text), math_tokens


def markdown_to_fragment(md_text: str, math_tokens: Optional[Dict[str, Dict[str, str]]] = None) -> str:
    safe_md, extracted_tokens = prepare_markdown(md_text)
    if math_tokens is not None:
        math_tokens.update(extracted_tokens)
    return markdown.markdown(
        safe_md,
        extensions=["extra", "sane_lists", "smarty", "footnotes"],
        output_format="html5",
    )


def clean_attrs(tag: Tag) -> None:
    allowed = ALLOWED_ATTRS.get(tag.name, set())
    preserved = {key: value for key, value in tag.attrs.items() if key in allowed}
    if "id" in tag.attrs:
        preserved["id"] = tag.attrs["id"]
    if "style" in tag.attrs:
        preserved["style"] = tag.attrs["style"]
    tag.attrs.clear()
    tag.attrs.update(preserved)


def apply_inline_styles(fragment: str, styles_map: Dict[str, str]) -> str:
    soup = BeautifulSoup(fragment, "html.parser")

    for tag in list(soup.find_all(True)):
        clean_attrs(tag)
        style_key = "code_block" if tag.name == "code" and tag.parent and tag.parent.name == "pre" else tag.name
        style = styles_map.get(style_key, "")
        if style:
            tag["style"] = style

    return "\n".join(str(child) for child in soup.contents)


def replace_enhanced_text_nodes(
    soup: BeautifulSoup,
    styles_map: Dict[str, str],
    math_tokens: Dict[str, Dict[str, str]],
) -> None:
    token_re = re.compile(r"@@P2W_MATH_(?:INLINE|BLOCK)_\d+@@")
    highlight_re = re.compile(r"==(.+?)==")
    combined_re = re.compile(r"(@@P2W_MATH_(?:INLINE|BLOCK)_\d+@@|==.+?==)")

    for text_node in list(soup.find_all(string=True)):
        parent = text_node.parent
        if parent and parent.name in {"code", "pre"}:
            continue

        text = str(text_node)
        if not token_re.search(text) and not highlight_re.search(text):
            continue

        pieces = combined_re.split(text)
        new_nodes = []
        for piece in pieces:
            if not piece:
                continue
            if piece in math_tokens:
                token = math_tokens[piece]
                tag = soup.new_tag("span")
                tag.string = token["value"]
                tag["style"] = styles_map.get(token["type"], "")
                new_nodes.append(tag)
            elif piece.startswith("==") and piece.endswith("=="):
                tag = soup.new_tag("mark")
                tag.string = piece[2:-2]
                style = styles_map.get("mark", "")
                if style:
                    tag["style"] = style
                new_nodes.append(tag)
            else:
                new_nodes.append(NavigableString(piece))

        for node in reversed(new_nodes):
            text_node.insert_after(node)
        text_node.extract()


def convert_md_to_html(md_text: str, styles_map: Dict[str, str], primary_color: str = "#20B2AA") -> str:
    if "strong" not in styles_map:
        styles_map = dict(styles_map)
        styles_map["strong"] = f"color:{primary_color}; font-weight:bold;"
    math_tokens: Dict[str, Dict[str, str]] = {}
    fragment = markdown_to_fragment(md_text, math_tokens)
    soup = BeautifulSoup(fragment, "html.parser")
    replace_enhanced_text_nodes(soup, styles_map, math_tokens)
    return apply_inline_styles("\n".join(str(child) for child in soup.contents), styles_map)


def wrap_html(html_body: str, styles_map: Dict[str, str]) -> str:
    section_style = styles_map.get("section", DEFAULT_STYLES["section"])
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>微信公众号文章</title>
</head>
<body style="margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue','PingFang SC','Microsoft YaHei',sans-serif; font-size:15px; line-height:1.75; color:#333;">
<section style="{section_style}">
{html_body}
</section>
</body>
</html>"""


def render_markdown_file(
    input_path: Path,
    output_path: Path,
    theme: str,
    template: Optional[str],
    inline_template: Optional[str],
    primary_color: str,
) -> None:
    md_text = input_path.read_text(encoding="utf-8")
    styles_map = load_styles(theme, template, inline_template, primary_color)
    html_body = convert_md_to_html(md_text, styles_map, primary_color)
    html = wrap_html(html_body, styles_map)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Markdown → 微信公众号HTML转换器")
    parser.add_argument("input", help="输入Markdown文件路径")
    parser.add_argument("--output", "-o", help="输出HTML文件路径（默认与输入同名.html）")
    parser.add_argument("--theme", "-t", choices=["default", "grace", "simple"], default="default", help="doocs/md主题")
    parser.add_argument("--template", help="自定义CSS模板文件路径")
    parser.add_argument("--inline-template", help="自定义内联样式 JSON 文件路径")
    parser.add_argument("--primary-color", "-c", default="#20B2AA", help="主题色")
    args = parser.parse_args(list(argv) if argv is not None else None)

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".html")
    render_markdown_file(
        input_path=input_path,
        output_path=output_path,
        theme=args.theme,
        template=args.template,
        inline_template=args.inline_template,
        primary_color=args.primary_color,
    )

    print(f"转换完成: {output_path}")
    print(f"主题: {args.template or 'doocs/' + args.theme}")
    print(f"主题色: {args.primary_color}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
