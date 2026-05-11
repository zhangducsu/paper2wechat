#!/usr/bin/env python3
"""
Markdown → 微信公众号HTML转换器
支持doocs/md主题样式和用户自定义模板

用法:
  python md2wechat.py input.md --theme default --primary-color #20B2AA
  python md2wechat.py input.md --template templates/themes/custom.css
"""

import re
import sys
import os
import argparse

# 默认CSS变量值（模拟doocs/md的CSS变量系统）
DEFAULT_VARS = {
    '--md-font-family': "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Microsoft YaHei', sans-serif",
    '--md-font-size': '15px',
    '--md-primary-color': '#20B2AA',
    '--foreground': '0 0% 0%',  # HSL black
    '--blockquote-background': 'rgba(0,0,0,0.03)',
}


def resolve_css_vars(css_text, variables=None):
    """将CSS变量替换为实际值"""
    if variables is None:
        variables = DEFAULT_VARS
    
    def replace_var(match):
        var_name = match.group(1)
        value = variables.get(var_name, match.group(0))
        # 处理 hsl(var(--foreground)) 格式
        if value.startswith('0 0%'):
            return 'hsl(0, 0%, 0%)'
        return value
    
    # 替换 var(--xxx) 格式
    result = re.sub(r'var\(([^)]+)\)', replace_var, css_text)
    # 替换 calc() 中的 var()
    result = re.sub(r'calc\(([^)]+)\)', lambda m: m.group(0), result)
    return result


def parse_css_to_inline_styles(css_text, primary_color=None):
    """将CSS规则解析为元素→内联样式的映射"""
    if primary_color:
        DEFAULT_VARS['--md-primary-color'] = primary_color
    
    css_text = resolve_css_vars(css_text)
    
    # 简化calc表达式
    css_text = re.sub(r'calc\((var\(--md-font-size\)) \* ([\d.]+)\)', 
                      lambda m: f"{float(m.group(2)) * 15}px", css_text)
    css_text = re.sub(r'calc\((var\(--md-font-size\)) \* ([\d.]+)\)',
                      lambda m: f"{float(m.group(2)) * 15}px", css_text)
    
    styles_map = {}
    
    # 解析CSS规则
    pattern = r'([^{}]+)\{([^{}]+)\}'
    for match in re.finditer(pattern, css_text):
        selector = match.group(1).strip()
        declarations = match.group(2).strip()
        
        # 跳过伪元素和复杂选择器
        if ':' in selector and not selector.startswith(':'):
            continue
        if selector.startswith('.') and ' ' in selector:
            continue
        if selector.startswith('#'):
            continue
        
        # 清理声明
        clean_decls = []
        for decl in declarations.split(';'):
            decl = decl.strip()
            if not decl or decl.startswith('/*'):
                continue
            # 跳过不兼容的属性
            if any(skip in decl for skip in ['display: table', '-webkit-', 'transform-origin', 'transform: scale']):
                continue
            if 'var(' in decl:
                continue
            clean_decls.append(decl)
        
        if clean_decls:
            # 提取标签名
            tag = selector.split(',')[0].strip().split(' ')[0].split('>')[0].strip()
            styles_map[tag] = '; '.join(clean_decls)
    
    return styles_map


def convert_md_to_html(md_text, styles_map, primary_color='#20B2AA'):
    """将Markdown转换为带内联样式的HTML"""
    # 加粗文字的统一颜色
    strong_style = f'color:{primary_color}; font-weight:bold;'
    # 引用块默认样式
    blockquote_default = f'font-style:normal; padding:1em; border-left:4px solid {primary_color}; border-radius:6px; background:rgba(0,0,0,0.03); margin-bottom:1em;'
    lines = md_text.split('\n')
    html_lines = []
    in_list = False
    in_blockquote = False
    in_table = False
    in_code_block = False
    
    for line in lines:
        stripped = line.strip()
        
        # 代码块
        if stripped.startswith('```'):
            if in_code_block:
                html_lines.append('</code></pre>')
                in_code_block = False
            else:
                html_lines.append('<pre style="font-size:90%; overflow-x:auto; border-radius:8px; padding:0.5em 1em 1em; background:#f6f8fa; margin:10px 8px;"><code style="font-size:90%; color:#d14; background:none; white-space:pre-wrap;">')
                in_code_block = True
            continue
        
        if in_code_block:
            html_lines.append(stripped)
            continue
        
        # 空行
        if not stripped:
            if in_list:
                html_lines.append('</ul>' if html_lines[-2].startswith('<li') or '<ul>' in ''.join(html_lines[-5:]) else '</ol>')
                in_list = False
            if in_blockquote:
                html_lines.append('</p></blockquote>')
                in_blockquote = False
            if in_table:
                html_lines.append('</table>')
                in_table = False
            continue
        
        # 标题
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            tag = f'h{level}'
            style = styles_map.get(tag, '')
            html_lines.append(f'<{tag} style="{style}">{text}</{tag}>')
            continue
        
        # 引用块
        if stripped.startswith('>'):
            if not in_blockquote:
                style = styles_map.get('blockquote', blockquote_default)
                html_lines.append(f'<blockquote style="{style}"><p style="margin:0; letter-spacing:0.1em;">')
                in_blockquote = True
            content = stripped.lstrip('> ').strip()
            # 处理加粗
            content = re.sub(r'\*\*(.+?)\*\*', rf'<strong style="{strong_style}">\1</strong>', content)
            html_lines.append(content)
            continue
        
        # 图片
        img_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', stripped)
        if img_match:
            alt = img_match.group(1)
            src = img_match.group(2)
            style = styles_map.get('img', 'display:block; max-width:100%; margin:0.1em auto 0.5em; border-radius:4px;')
            html_lines.append(f'<img src="{src}" alt="{alt}" style="{style}" />')
            # 图注
            continue
        
        # 分隔线
        if stripped in ['---', '***', '___']:
            style = 'border-style:solid; border-width:2px 0 0; border-color:rgba(0,0,0,0.1); height:0.4em; margin:1.5em 0;'
            html_lines.append(f'<hr style="{style}" />')
            continue
        
        # 表格
        if stripped.startswith('|'):
            if not in_table:
                html_lines.append('<table style="border-collapse:collapse; margin:1.5em 8px; width:100%;">')
                in_table = True
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            is_header = all(c.replace('-', '').replace(':', '') == '' for c in cells)
            if is_header:
                continue
            tag = 'th' if not any('<td' in l for l in html_lines[-3:]) and '<tr>' not in ''.join(html_lines[-5:]) else 'td'
            if tag == 'th':
                style = 'border:1px solid #dfdfdf; padding:0.25em 0.5em; font-weight:bold; background:rgba(0,0,0,0.05);'
            else:
                style = 'border:1px solid #dfdfdf; padding:0.25em 0.5em;'
            row = ''.join(f'<{tag} style="{style}">{c}</{tag}>' for c in cells)
            html_lines.append(f'<tr>{row}</tr>')
            continue
        
        # 无序列表
        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                style = styles_map.get('ul', 'list-style:circle; padding-left:1em; margin-left:0;')
                html_lines.append(f'<ul style="{style}">')
                in_list = True
            content = stripped[2:]
            content = re.sub(r'\*\*(.+?)\*\*', rf'<strong style="{strong_style}">\1</strong>', content)
            html_lines.append(f'<li style="display:block; margin:0.2em 8px;">{content}</li>')
            continue
        
        # 有序列表
        ol_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if ol_match:
            if not in_list:
                style = styles_map.get('ol', 'padding-left:1em; margin-left:0;')
                html_lines.append(f'<ol style="{style}">')
                in_list = True
            content = ol_match.group(2)
            content = re.sub(r'\*\*(.+?)\*\*', rf'<strong style="{strong_style}">\1</strong>', content)
            html_lines.append(f'<li style="display:block; margin:0.2em 8px;">{content}</li>')
            continue
        
        # 普通段落
        style = styles_map.get('p', 'margin:1.5em 8px; letter-spacing:0.1em;')
        # 处理行内格式
        content = re.sub(r'\*\*(.+?)\*\*', rf'<strong style="{strong_style}">\1</strong>', stripped)
        content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
        content = re.sub(r'`([^`]+)`', r'<code style="font-size:90%; color:#d14; background:rgba(27,31,35,0.05); padding:3px 5px; border-radius:4px;">\1</code>', content)
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:#576b95; text-decoration:none;">\1</a>', content)
        html_lines.append(f'<p style="{style}">{content}</p>')
    
    # 关闭未闭合的标签
    if in_list:
        html_lines.append('</ul>')
    if in_blockquote:
        html_lines.append('</p></blockquote>')
    if in_table:
        html_lines.append('</table>')
    
    return '\n'.join(html_lines)


def main():
    parser = argparse.ArgumentParser(description='Markdown → 微信公众号HTML转换器')
    parser.add_argument('input', help='输入Markdown文件路径')
    parser.add_argument('--output', '-o', help='输出HTML文件路径（默认与输入同名.html）')
    parser.add_argument('--theme', '-t', choices=['default', 'grace', 'simple'], default='default', help='doocs/md主题（默认default）')
    parser.add_argument('--template', help='自定义CSS模板文件路径')
    parser.add_argument('--primary-color', '-c', default='#20B2AA', help='主题色（默认#20B2AA）')
    
    args = parser.parse_args()
    
    # 读取Markdown
    with open(args.input, 'r', encoding='utf-8') as f:
        md_text = f.read()
    
    # 读取CSS
    if args.template:
        css_path = args.template
        with open(css_path, 'r', encoding='utf-8') as f:
            css_text = f.read()
    else:
        theme_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates', 'themes')
        # 先加载 base.css 作为基础层，再加载具体主题作为覆盖层
        base_path = os.path.join(theme_dir, 'doocs_base.css')
        theme_path = os.path.join(theme_dir, f'doocs_{args.theme}.css')
        css_text = ''
        if os.path.exists(base_path):
            with open(base_path, 'r', encoding='utf-8') as f:
                css_text += f.read() + '\n'
        with open(theme_path, 'r', encoding='utf-8') as f:
            css_text += f.read()
    
    # 解析CSS为内联样式
    styles_map = parse_css_to_inline_styles(css_text, args.primary_color)
    
    # 转换
    html_body = convert_md_to_html(md_text, styles_map, args.primary_color)
    
    # 包装完整HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>微信公众号文章</title>
</head>
<body style="margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue','PingFang SC','Microsoft YaHei',sans-serif; font-size:15px; line-height:1.75; color:#333;">
<section style="padding:16px; max-width:100%; box-sizing:border-box;">
{html_body}
</section>
</body>
</html>'''
    
    # 输出
    output_path = args.output or args.input.rsplit('.', 1)[0] + '.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 转换完成: {output_path}")
    print(f"   主题: {args.template or 'doocs/' + args.theme}")
    print(f"   主题色: {args.primary_color}")


if __name__ == '__main__':
    main()
