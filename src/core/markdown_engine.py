"""
Markdown 渲染引擎 —— 将 Markdown 源码转换为 HTML。
支持扩展语法（表格、代码高亮、脚注等）。
"""

from markdown import Markdown
from markdown.extensions import Extension


class MarkdownEngine:
    """Markdown → HTML 转换引擎。"""

    def __init__(self):
        self._md: Markdown | None = None
        self._setup()

    def _setup(self) -> None:
        """配置 Markdown 解析器及扩展。"""
        extensions: list[str | Extension] = [
            "fenced_code",          # 围栏代码块
            "tables",               # 表格
            "toc",                  # 目录
            "codehilite",           # 代码高亮（Pygments）
            "nl2br",                # 换行转 <br>
            "sane_lists",           # 更合理的列表解析
            "footnotes",            # 脚注
        ]

        extension_configs = {
            "codehilite": {
                "css_class": "highlight",
                "guess_lang": True,
                "use_pygments": True,
            },
        }

        self._md = Markdown(
            extensions=extensions,
            extension_configs=extension_configs,
            output_format="html",
        )

    def convert(self, markdown_text: str) -> str:
        """将 Markdown 文本转换为 HTML。

        Args:
            markdown_text: Markdown 格式的原始文本。

        Returns:
            转换后的 HTML 字符串。
        """
        self._md.reset()
        return self._md.convert(markdown_text)

    def wrap_html(self, html_body: str, title: str = "预览") -> str:
        """将 HTML body 包装为完整的 HTML 文档，
        嵌入 Pygments 代码高亮 CSS 和预览样式。

        Args:
            html_body: Markdown 转换得到的 HTML body 内容。
            title: 页面标题。

        Returns:
            完整的 HTML 文档字符串。
        """
        try:
            from pygments.formatters import HtmlFormatter
            code_css = HtmlFormatter().get_style_defs(".highlight")
        except ImportError:
            code_css = ""

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{code_css}

body {{
    font-family: "Microsoft YaHei", "PingFang SC", -apple-system, sans-serif;
    font-size: 15px;
    line-height: 1.8;
    color: #333;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}}

h1, h2, h3, h4, h5, h6 {{
    color: #222;
    margin-top: 1.2em;
    margin-bottom: 0.6em;
    line-height: 1.4;
}}

h1 {{ font-size: 1.8em; border-bottom: 2px solid #4a90d9; padding-bottom: 8px; }}
h2 {{ font-size: 1.5em; border-bottom: 1px solid #ddd; padding-bottom: 6px; }}
h3 {{ font-size: 1.3em; }}

p {{ margin: 0.6em 0; }}

a {{
    color: #4a90d9;
    text-decoration: none;
}}

a:hover {{ text-decoration: underline; }}

code {{
    background: #f4f4f4;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 0.9em;
    color: #c7254e;
}}

pre {{
    background: #f8f8f8;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 16px;
    overflow-x: auto;
}}

pre code {{
    background: none;
    padding: 0;
    color: inherit;
}}

blockquote {{
    border-left: 4px solid #4a90d9;
    margin: 1em 0;
    padding: 0.5em 1em;
    background: #f0f6ff;
    color: #555;
}}

table {{
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}}

th, td {{
    border: 1px solid #ddd;
    padding: 8px 12px;
    text-align: left;
}}

th {{
    background: #4a90d9;
    color: white;
    font-weight: 600;
}}

tr:nth-child(even) {{ background: #f9f9f9; }}

img {{
    max-width: 100%;
    border-radius: 4px;
}}

ul, ol {{ padding-left: 2em; }}

li {{ margin: 0.3em 0; }}

hr {{
    border: none;
    border-top: 2px solid #eee;
    margin: 2em 0;
}}

/* 暗色主题适配 */
body.dark {{
    background: #1e1e1e;
    color: #ccc;
}}

body.dark h1, body.dark h2, body.dark h3,
body.dark h4, body.dark h5, body.dark h6 {{
    color: #eee;
}}

body.dark h1 {{ border-bottom-color: #569cd6; }}
body.dark h2 {{ border-bottom-color: #444; }}

body.dark code {{
    background: #2d2d2d;
    color: #f48771;
}}

body.dark pre {{
    background: #2d2d2d;
    border-color: #444;
}}

body.dark blockquote {{
    background: #252526;
    border-left-color: #569cd6;
    color: #aaa;
}}

body.dark th {{ background: #264f78; }}
body.dark td {{ border-color: #444; }}
body.dark tr:nth-child(even) {{ background: #252525; }}

body.dark a {{ color: #569cd6; }}
body.dark hr {{ border-top-color: #444; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
