"""
Markdown 渲染引擎 —— 将 Markdown 源码转换为 HTML。
支持扩展语法（表格、代码高亮、脚注、LaTeX 公式等）。
"""

from markdown import Markdown
from markdown.extensions import Extension


# ═══════════════════════════════════════════════════════════════
#  主题 CSS
# ═══════════════════════════════════════════════════════════════

# ── 默认主题（亮色）预览 CSS ──────────────────────────────

_DEFAULT_PREVIEW_LIGHT_CSS = """
body {
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", -apple-system, sans-serif;
    font-size: 15px;
    line-height: 1.8;
    color: #333;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}
h1, h2, h3, h4, h5, h6 {
    color: #222;
    margin-top: 1.2em;
    margin-bottom: 0.6em;
    line-height: 1.4;
}
h1 { font-size: 1.8em; border-bottom: 2px solid #4a90d9; padding-bottom: 8px; }
h2 { font-size: 1.5em; border-bottom: 1px solid #ddd; padding-bottom: 6px; }
h3 { font-size: 1.3em; }
p { margin: 0.6em 0; }
a { color: #4a90d9; text-decoration: none; }
a:hover { text-decoration: underline; }
code {
    background: #f4f4f4; padding: 2px 6px; border-radius: 3px;
    font-family: "Cascadia Code", "Consolas", "Courier New", "DejaVu Sans Mono", monospace;
    font-size: 0.9em; color: #c7254e;
}
pre {
    background: #f8f8f8; border: 1px solid #ddd;
    border-radius: 6px; padding: 16px; overflow-x: auto;
}
pre code { background: none; padding: 0; color: inherit; }
blockquote {
    border-left: 4px solid #4a90d9; margin: 1em 0;
    padding: 0.5em 1em; background: #f0f6ff; color: #555;
}
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
th { background: #4a90d9; color: white; font-weight: 600; }
tr:nth-child(even) { background: #f9f9f9; }
img { max-width: 100%; border-radius: 4px; }
ul, ol { padding-left: 2em; }
li { margin: 0.3em 0; }
hr { border: none; border-top: 2px solid #eee; margin: 2em 0; }
"""

# ── 默认主题暗色预览适配 ─────────────────────────────────

_DEFAULT_PREVIEW_DARK_CSS = """
body.dark { background: #1e1e1e; color: #e0e0e0; }
body.dark h1, body.dark h2, body.dark h3,
body.dark h4, body.dark h5, body.dark h6 { color: #eee; }
body.dark h1 { border-bottom-color: #569cd6; }
body.dark h2 { border-bottom-color: #444; }
body.dark code { background: #252526; color: #f48771; }
body.dark pre { background: #151515; border-color: #3e3e3e; }
body.dark pre code { background: transparent; }
body.dark blockquote { background: #252526; border-left-color: #569cd6; color: #bbb; }
body.dark th { background: #264f78; }
body.dark td { border-color: #444; }
body.dark tr:nth-child(even) { background: #252525; }
body.dark a { color: #6db3f2; }
body.dark hr { border-top-color: #444; }
"""

# ── 数学公式高亮标记（仅预览） ──────────────────────────

_MATH_PREVIEW_LIGHT_CSS = """
.arithmatex {
    display: inline-block; background: #f3e8ff;
    border: 1px dashed #c4a2e8; border-radius: 4px;
    padding: 1px 6px; font-family: "Consolas", "Courier New", monospace;
    font-size: 0.92em; color: #6b21a8; margin: 0 1px;
}
div.arithmatex {
    display: block; background: #f5f0ff; border: 1px solid #d4c0f0;
    border-radius: 6px; padding: 12px 16px; margin: 1em 0;
    overflow-x: auto; text-align: center; font-size: 1.05em;
}
"""

_MATH_PREVIEW_DARK_CSS = """
body.dark .arithmatex { background: #1e1830; border-color: #6b3fa0; color: #c4a2e8; }
body.dark div.arithmatex { background: #1a1530; border-color: #5a3a8a; }
"""

# ═══════════════════════════════════════════════════════════════
#  LaTeX 学术主题 CSS（从 Typora LaTeX Theme 适配）
#  预览版：CSS 变量已解析为确定值，移除 QTextBrowser 不支持的
#          counter / flex / @supports / @media 等特性。
#  导出版：保留完整 CSS（浏览器中渲染效果最佳）。
# ═══════════════════════════════════════════════════════════════

_LATEX_PREVIEW_LIGHT_CSS = """
/* ═══ LaTeX 学术主题 · 亮色（预览适配版） ═══ */

body {
    font-family: "Latin Modern Roman", "Latin Modern Roman 10", Times,
                 "家族宋", "宋体-简", "华文宋体", serif;
    font-size: 12pt;
    line-height: 1.618em;
    color: #222;
    background: white;
    max-width: 21cm;
    margin: 0 auto;
    padding: 1.8cm 2cm 1.6cm 2cm;
    text-align: justify;
}

/* ── 标题 ── */
h1, h2, h3, h4, h5, h6 {
    font-weight: bold;
    font-family: "Latin Modern Roman", "Latin Modern Roman 10", Times,
                 "华文黑体", "微软雅黑", serif;
}
h1 {
    text-align: center;
    font-size: 1.9em;
}
h2 { font-size: 1.5em; }
h3 { font-size: 1.25em; }
h4 {
    font-size: 1.15em;
    font-family: "Latin Modern Roman", "Latin Modern Roman 10", Times,
                 "华文楷体", "楷体", serif;
}
h5 {
    font-size: 1.10em;
    font-family: "Latin Modern Roman", "Latin Modern Roman 10", Times,
                 "华文仿宋", "仿宋", serif;
}
h6 {
    font-size: 1.05em;
    font-family: "Latin Modern Roman", "Latin Modern Roman 10", Times,
                 "华文仿宋", "仿宋", serif;
}

/* ── 正文 ── */
p { margin-top: 1em; margin-bottom: 1em; text-align: justify; }
strong { font-weight: 900; }
a { color: #2E67D3; }
hr { border-top: solid 1px #ddd; margin-top: 1.8em; margin-bottom: 1.8em; }

/* ── 行内代码 ── */
code {
    font-family: "Latin Modern Mono", "Latin Modern Mono 10", "Consolas",
                 "Courier New", monospace;
}
h1 code, h2 code, h3 code, h4 code, h5 code, h6 code,
p code, li code {
    color: rgb(60, 112, 198); background-color: #fefefe;
    box-shadow: 0 0 1px 1px #c8d3df;
    border-radius: 2px; margin: 0 2px; padding: 0 2px;
}

/* ── 代码块 ── */
pre {
    font-size: 1em; font-family: "Latin Modern Mono", "Latin Modern Mono 10",
                 "Consolas", "Courier New", monospace;
    padding: 1.4em; background: #f8f8f8; border: 1px solid #e0e0e0;
    border-radius: 4px; overflow-x: auto; margin: 1em 0;
}
pre code { background: none; padding: 0; color: inherit;
           box-shadow: none; border-radius: 0; margin: 0; }

/* ── 引用 ── */
blockquote {
    font-style: normal;
    font-family: "Latin Modern Roman", "Latin Modern Roman 10", Times,
                 "华文仿宋", "STFangsong", serif;
    font-size: 1.05em;
    border-left: 4px solid hsl(0, 0%, 70%);
    padding-left: 2em; padding-right: 2em; margin-left: 0;
}
blockquote blockquote { font-size: inherit; padding-right: 0; }

/* ── 三线表 ── */
table {
    border-top: 1.2pt solid #222;
    border-bottom: 1.2pt solid #222;
    font-family: "Latin Modern Roman", "Latin Modern Roman 10", Times,
                 "家族宋", "宋体-简", "华文宋体", serif;
    text-align: center; width: auto; margin: 0 auto;
    border-spacing: 6px;
}
thead {
    font-family: "Latin Modern Roman", "Latin Modern Roman 10", Times,
                 "华文黑体", "微软雅黑", serif;
    font-weight: 900;
}
/* 三线表中线画在 th 下边框上（QTextBrowser 不支持 thead 的 border） */
th {
    padding: 4px 6px;
    border-bottom: 0.5pt solid #222;
}
td { padding: 2px 6px; }

/* ── 列表 ── */
ul { list-style: disc; padding-left: 2em; }
ol { list-style: decimal; padding-left: 2em; }
li { margin: 0.2em 0; }

/* ── 图片 ── */
img { max-width: 100%; }

/* ── 公式 ── */
.arithmatex {
    display: inline; font-size: 1em;
    font-family: "Latin Modern Roman", "Latin Modern Roman 10", Times, serif;
}
div.arithmatex { display: block; text-align: center; margin: 1em 0; font-size: 1em; }
.MathJax { font-size: 1em; }
"""

# ── LaTeX 主题暗色预览适配 ─────────────────────────────

_LATEX_PREVIEW_DARK_CSS = """
body.dark {
    background: #1e1e1e; color: #e0e0e0;
}
body.dark h1, body.dark h2, body.dark h3,
body.dark h4, body.dark h5, body.dark h6 { color: #dddddd; }
body.dark a { color: #8bb1f9; }
body.dark hr { border-top-color: #888888; }
body.dark h1 code, body.dark h2 code, body.dark h3 code,
body.dark h4 code, body.dark h5 code, body.dark h6 code,
body.dark p code, body.dark li code {
    color: #8bb1f9; background-color: #161616;
    box-shadow: 0 0 1px 1px #141414;
}
body.dark pre { background: #151515; border-color: #444; }
body.dark pre code,
body.dark .highlight,
body.dark .highlight * { background: transparent; }
body.dark blockquote { border-left-color: #888888; }
body.dark table { border-top-color: #ccc; border-bottom-color: #ccc; }
body.dark th { border-bottom-color: #ccc; }
body.dark .arithmatex { color: #dcdcdc; }
"""

# ── LaTeX 主题导出 CSS（完整版，保留 CSS 变量、计数器等） ──
# 直接内联编译后的 Typora LaTeX Theme，浏览器打开时全特性生效

_LATEX_EXPORT_CSS = """
/* ═══ LaTeX 学术主题 · 导出 ═══
   基于 Keldos-Li/typora-latex-theme (MIT License)
   https://github.com/Keldos-Li/typora-latex-theme */
:root {
  --blockquote-border-enabled: 1;
  --blockquote-border-color: hsl(0, 0%, 70%);
  --base-latin-font: "Latin Modern Roman", "Latin Modern Roman 10", Times;
  --base-chinese-font: "家族宋", "宋体-简", "华文宋体";
  --base-font-size: 9.5pt;
  --quote-latin-font: "Latin Modern Roman", "Latin Modern Roman 10", Times, "Times New Roman";
  --quote-chinese-font: "华文仿宋", "STFangsong";
  --quote-font-size: 1.05em;
  --code-font: "Latin Modern Mono", "Latin Modern Mono 10", "Consolas", "Courier New";
  --ui-font: "阿里巴巴普惠体 2.0", "微软雅黑";
  --sourceMode-font: "SF Mono", "阿里巴巴普惠体 2.0", "微软雅黑";
  --toc-font: "";
  --toc-font-size: "";
  --math-font-size: 1em;
  --table-title-font: "";
  --table-font: "";
  --heading-chinese-sans-serif-font: "华文黑体";
  --heading-chinese-kai-font: "华文楷体";
  --heading-chinese-fangsong-font: "华文仿宋";
  --heading-latin-font: var(--base-latin-font);
  --heading-chinese-font: var(--heading-chinese-sans-serif-font);
  --title-chinese-font: var(--heading-chinese-sans-serif-font);
  --title-font-size: 1.9em;
  --h2-chinese-font: var(--heading-chinese-sans-serif-font);
  --h2-font-size: 1.5em;
  --h3-chinese-font: var(--heading-chinese-sans-serif-font);
  --h3-font-size: 1.25em;
  --h4-chinese-font: var(--heading-chinese-kai-font);
  --h4-font-size: 1.15em;
  --h5-chinese-font: var(--heading-chinese-fangsong-font);
  --h5-font-size: 1.10em;
  --h6-chinese-font: var(--heading-chinese-fangsong-font);
  --h6-font-size: 1.05em;
  --strong-weight: 900;
  --base-line-height: 1.618em;
  --set-margin: 1.8cm 2cm 1.6cm 2cm;
  --toc-show-title: none;
  --link-color-light: #2E67D3;
  --link-color-dark: #8bb1f9;
  --page-break-before-h2: auto;
}
body {
    font-family: var(--base-latin-font), var(--base-chinese-font), serif;
    font-size: var(--base-font-size);
    line-height: var(--base-line-height);
    max-width: 21cm;
    margin: 0 auto;
    padding: var(--set-margin);
    background: white; color: #222;
}
h1, h2, h3, h4, h5, h6 { font-weight: bold; }
h1 { font-family: var(--heading-latin-font), var(--title-chinese-font), serif;
     text-align: center; font-size: var(--title-font-size); }
h2 { font-family: var(--heading-latin-font), var(--h2-chinese-font), serif;
     font-size: var(--h2-font-size); }
h3 { font-family: var(--heading-latin-font), var(--h3-chinese-font), serif;
     font-size: var(--h3-font-size); }
h4 { font-family: var(--heading-latin-font), var(--h4-chinese-font), serif;
     font-size: var(--h4-font-size); }
h5 { font-family: var(--heading-latin-font), var(--h5-chinese-font), serif;
     font-size: var(--h5-font-size); }
h6 { font-family: var(--heading-latin-font), var(--h6-chinese-font), serif;
     font-size: var(--h6-font-size); }
p { margin-top: 1em; margin-bottom: 1em; text-align: justify; }
strong { font-weight: var(--strong-weight); }
a { color: var(--link-color-light); }
hr { border-top: solid 1px #ddd; margin-top: 1.8em; margin-bottom: 1.8em; }
code { font-family: var(--code-font), var(--ui-font), monospace; }
h1 code, h2 code, h3 code, h4 code, h5 code, h6 code, p code, li code {
    color: rgb(60, 112, 198); background-color: #fefefe;
    box-shadow: 0 0 1px 1px #c8d3df; border-radius: 2px; margin: 0 2px; padding: 0 2px;
}
pre { font-size: 1em; overflow-x: auto; }
pre code { background: none; padding: 0; box-shadow: none; border-radius: 0; margin: 0; }
blockquote {
    font-style: normal;
    font-family: var(--quote-latin-font), var(--quote-chinese-font),
                 var(--base-latin-font), var(--base-chinese-font), serif;
    font-size: var(--quote-font-size);
    border-left: 4px solid var(--blockquote-border-color);
    padding-left: 2em; padding-right: 2em; margin-left: 0;
}
table {
    border-top: 1.2pt solid; border-bottom: 1.2pt solid;
    font-family: var(--table-font), var(--base-latin-font), var(--base-chinese-font), serif;
    text-align: center; width: auto; margin: 0 auto; border-spacing: 6px;
}
thead { border-bottom: 0.5pt solid; font-weight: var(--strong-weight); }
th { padding: 0 6px; }
td { padding: 2px; }
ul, ol { padding-left: 2em; }
li { margin: 0.2em 0; }
img { max-width: 100%; }
.MathJax { font-size: var(--math-font-size); }
.arithmatex { font-size: var(--math-font-size); }
div.arithmatex { text-align: center; margin: 1em 0; }
"""


# ═══════════════════════════════════════════════════════════════
#  MarkdownEngine
# ═══════════════════════════════════════════════════════════════


class MarkdownEngine:
    """Markdown → HTML 转换引擎。"""

    # 可用主题
    THEMES = ("default", "latex")

    def __init__(self):
        self._md: Markdown | None = None
        self._code_css: str = ""
        self._theme: str = "default"
        self._setup()

    # ── 属性 ──────────────────────────────────────────

    @property
    def theme(self) -> str:
        return self._theme

    @theme.setter
    def theme(self, value: str) -> None:
        if value not in self.THEMES:
            raise ValueError(f"未知主题: {value}，可用: {self.THEMES}")
        self._theme = value

    # ── 初始化 ────────────────────────────────────────

    def _setup(self) -> None:
        """配置 Markdown 解析器及扩展，并预生成 Pygments CSS。"""
        extensions: list[str | Extension] = [
            "fenced_code",
            "tables",
            "toc",
            "codehilite",
            "nl2br",
            "sane_lists",
            "footnotes",
            "pymdownx.arithmatex",
        ]

        extension_configs = {
            "codehilite": {
                "css_class": "highlight",
                "guess_lang": True,
                "use_pygments": True,
            },
            "pymdownx.arithmatex": {
                "generic": True,
            },
        }

        self._md = Markdown(
            extensions=extensions,
            extension_configs=extension_configs,
            output_format="html",
        )

        # 预生成 Pygments 代码高亮 CSS（初始化时执行一次，避免每次预览重复构造）
        try:
            from pygments.formatters import HtmlFormatter
            self._code_css = HtmlFormatter(nobackground=True).get_style_defs(".highlight")
            # 暗色模式使用 monokai 主题
            self._code_css_dark = HtmlFormatter(
                nobackground=True, style="monokai"
            ).get_style_defs("body.dark .highlight")
        except ImportError:
            self._code_css = ""
            self._code_css_dark = ""

    # ── 转换 ──────────────────────────────────────────

    def convert(self, markdown_text: str) -> str:
        self._md.reset()
        return self._md.convert(markdown_text)

    def wrap_html(
        self,
        html_body: str,
        title: str = "预览",
        preview_mode: bool = False,
        theme: str | None = None,
        font_face_css: str = "",
        dark_mode: bool = False,
    ) -> str:
        """将 HTML body 包装为完整的 HTML 文档。

        Args:
            html_body: Markdown 转换得到的 HTML body 内容。
            title: 页面标题。
            preview_mode: 是否用于预览面板（True 时注入公式/主题高亮 CSS）。
            theme: 主题名称 ("default" / "latex")，为 None 时使用引擎当前主题。
            font_face_css: 额外的 @font-face CSS（字体管理器提供）。
            dark_mode: 是否使用暗色模式（为 body 添加 .dark 类以激活暗色 CSS）。

        Returns:
            完整的 HTML 文档字符串。
        """
        theme_name = theme or self._theme
        body_tag = '<body class="dark">' if dark_mode else "<body>"

        if theme_name == "latex":
            return self._wrap_latex(html_body, title, preview_mode,
                                    font_face_css, body_tag)
        return self._wrap_default(html_body, title, preview_mode,
                                  font_face_css, body_tag)

    # ── 默认主题包装 ──────────────────────────────────

    def _wrap_default(
        self, html_body: str, title: str, preview_mode: bool,
        font_face_css: str, body_tag: str,
    ) -> str:
        math_css = (
            _MATH_PREVIEW_LIGHT_CSS + _MATH_PREVIEW_DARK_CSS
            if preview_mode else ""
        )
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script>
MathJax = {{
  tex: {{ inlineMath: [['$','$'], ['\\\\(','\\\\)']] }},
  options: {{ enableMenu: false }}
}};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async>
</script>
<style>
{self._code_css}
{self._code_css_dark}
{font_face_css}
{_DEFAULT_PREVIEW_LIGHT_CSS}
{math_css}
{_DEFAULT_PREVIEW_DARK_CSS}
</style>
</head>
{body_tag}
{html_body}
</body>
</html>"""

    # ── LaTeX 主题包装 ────────────────────────────────

    def _wrap_latex(
        self, html_body: str, title: str, preview_mode: bool,
        font_face_css: str, body_tag: str,
    ) -> str:
        if preview_mode:
            body_css = _LATEX_PREVIEW_LIGHT_CSS
            dark_css = _LATEX_PREVIEW_DARK_CSS
            math_css = _MATH_PREVIEW_LIGHT_CSS + _MATH_PREVIEW_DARK_CSS
        else:
            body_css = _LATEX_EXPORT_CSS
            dark_css = ""
            math_css = ""

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script>
MathJax = {{
  tex: {{ inlineMath: [['$','$'], ['\\\\(','\\\\)']] }},
  options: {{ enableMenu: false }}
}};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async>
</script>
<style>
{self._code_css}
{self._code_css_dark}
{font_face_css}
{body_css}
{math_css}
{dark_css}
html {{ overflow-x: hidden; }}
pre {{ overflow-x: auto; }}
</style>
</head>
{body_tag}
{html_body}
</body>
</html>"""
