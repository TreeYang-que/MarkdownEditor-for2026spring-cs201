"""
Markdown 引擎单元测试。
"""

import sys
from pathlib import Path

# 确保项目根目录在 path 中
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.markdown_engine import MarkdownEngine


class TestMarkdownEngine:
    """MarkdownEngine 测试用例。"""

    @classmethod
    def setup_class(cls):
        cls.engine = MarkdownEngine()

    def test_bold(self):
        html = self.engine.convert("**粗体**")
        assert "<strong>粗体</strong>" in html

    def test_italic(self):
        html = self.engine.convert("*斜体*")
        assert "<em>斜体</em>" in html

    def test_heading_h1(self):
        html = self.engine.convert("# 标题")
        assert "<h1" in html and "标题</h1>" in html

    def test_heading_h2(self):
        html = self.engine.convert("## 标题")
        assert "<h2" in html and "标题</h2>" in html

    def test_code_inline(self):
        html = self.engine.convert("`code`")
        assert "<code>code</code>" in html

    def test_code_block(self):
        md = "```python\nprint('hello')\n```"
        html = self.engine.convert(md)
        assert "print" in html
        assert "highlight" in html.lower() or "<pre>" in html

    def test_unordered_list(self):
        html = self.engine.convert("- 项目1\n- 项目2")
        assert "<ul>" in html
        assert "<li>项目1</li>" in html
        assert "<li>项目2</li>" in html

    def test_ordered_list(self):
        html = self.engine.convert("1. 第一\n2. 第二")
        assert "<ol>" in html
        assert "<li>第一</li>" in html

    def test_link(self):
        html = self.engine.convert("[Google](https://google.com)")
        assert '<a href="https://google.com">Google</a>' in html

    def test_image(self):
        html = self.engine.convert("![logo](img/logo.png)")
        assert '<img' in html
        assert 'src="img/logo.png"' in html

    def test_blockquote(self):
        html = self.engine.convert("> 引用文本")
        assert "<blockquote>" in html
        assert "引用文本" in html

    def test_horizontal_rule(self):
        html = self.engine.convert("---")
        assert "<hr" in html

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = self.engine.convert(md)
        assert "<table>" in html
        assert "<th>A</th>" in html
        assert "<td>1</td>" in html

    def test_empty_text(self):
        html = self.engine.convert("")
        assert html == ""

    def test_wrap_html(self):
        body = "<p>Hello</p>"
        full = self.engine.wrap_html(body, title="测试")
        assert "<!DOCTYPE html>" in full
        assert "<title>测试</title>" in full
        assert "<p>Hello</p>" in full
        assert "</html>" in full

    # ── 主题渲染 ────────────────────────────────────

    def test_latex_theme_preview(self):
        """LaTeX 主题预览模式：CSS 变量已解析为确定值。"""
        self.engine.theme = "latex"
        full = self.engine.wrap_html("<p>test</p>", preview_mode=True)
        assert "Latin Modern Roman" in full
        assert "1.618em" in full
        assert "var(--base-font-size)" not in full  # 变量已解析

    def test_latex_theme_export(self):
        """LaTeX 主题导出模式：保留 CSS 变量供浏览器使用。"""
        self.engine.theme = "latex"
        full = self.engine.wrap_html("<p>test</p>", preview_mode=False)
        assert "Latin Modern Roman" in full
        assert "var(--base-font-size)" in full  # 变量保留

    def test_default_theme(self):
        """默认主题不应包含 LaTeX 字体。"""
        self.engine.theme = "default"
        full = self.engine.wrap_html("<p>test</p>", preview_mode=True)
        assert "Latin Modern" not in full
        assert "Microsoft YaHei" in full

    # ── LaTeX 数学公式 ──────────────────────────────

    def test_inline_math(self):
        html = self.engine.convert("质能方程 $E=mc^2$ 很著名")
        assert "arithmatex" in html
        assert "E=mc^2" in html

    def test_block_math(self):
        html = self.engine.convert("$$\n\\int_0^\\infty e^{-x} dx = 1\n$$")
        assert "arithmatex" in html
        assert "\\int" in html

    def test_math_with_underscore(self):
        html = self.engine.convert("$x_1 + x_2 = y$")
        assert "arithmatex" in html
        assert "x_1" in html

    def test_wrap_html_includes_mathjax(self):
        full = self.engine.wrap_html("<p>test</p>")
        assert "mathjax" in full.lower()

    def test_wrap_html_preview_mode_has_math_css(self):
        """预览模式应包含公式高亮 CSS（紫色背景标记）。"""
        self.engine.theme = "default"
        full = self.engine.wrap_html("<p>test</p>", preview_mode=True)
        assert "#f3e8ff" in full  # 紫色公式背景

    def test_wrap_html_export_mode_no_math_css(self):
        """导出模式不应包含预览专用的紫色公式高亮 CSS。"""
        self.engine.theme = "default"
        full = self.engine.wrap_html("<p>test</p>", preview_mode=False)
        assert "#f3e8ff" not in full  # 紫色公式背景不应出现

    # ── 逻辑块切分 ──────────────────────────────────

    def test_split_blocks_simple(self):
        """简单文本应正确切分为逻辑块。"""
        text = "第一段\n\n第二段"
        blocks = self.engine._split_blocks(text)
        assert len(blocks) == 2
        assert blocks[0]['text'] == "第一段"
        assert blocks[0]['start_line'] == 0
        assert blocks[0]['end_line'] == 0
        assert blocks[0]['index'] == 0
        assert blocks[1]['text'] == "第二段"
        assert blocks[1]['start_line'] == 2
        assert blocks[1]['end_line'] == 2
        assert blocks[1]['index'] == 1

    def test_split_blocks_fenced_code(self):
        """围栏代码块不应被内部空行切割。"""
        text = "开头\n\n```python\n\nprint('hello')\n\n```\n\n结尾"
        blocks = self.engine._split_blocks(text)
        assert len(blocks) == 3  # 开头、代码块、结尾
        assert blocks[0]['text'] == "开头"
        assert blocks[1]['text'] == "```python\n\nprint('hello')\n\n```"
        assert blocks[2]['text'] == "结尾"

    def test_split_blocks_empty_text(self):
        """空文本应返回空列表。"""
        blocks = self.engine._split_blocks("")
        assert blocks == []

    def test_split_blocks_only_blanks(self):
        """纯空白行文本应返回空列表。"""
        blocks = self.engine._split_blocks("\n\n\n")
        assert blocks == []

    def test_split_blocks_heading(self):
        """标题应作为独立块。"""
        text = "# 标题\n\n正文内容"
        blocks = self.engine._split_blocks(text)
        assert len(blocks) == 2
        assert blocks[0]['text'] == "# 标题"
        assert blocks[1]['text'] == "正文内容"

    # ── 锚点注入 ────────────────────────────────────

    def test_convert_with_anchors_basic(self):
        """基本文本应注入锚点标签。"""
        text = "# 标题\n\n正文"
        body, line_to_block = self.engine.convert_with_anchors(text)
        assert '<a id="md-b-0"' in body
        assert '<a id="md-b-1"' in body
        assert '<h1' in body
        assert '正文</p>' in body
        # 验证行→块映射
        assert line_to_block[0] == 0  # "# 标题" 在第 0 行
        assert line_to_block[2] == 1  # "正文" 在第 2 行

    def test_convert_with_anchors_fenced_code(self):
        """围栏代码块内空行不应切割块。"""
        text = "开头\n\n```\nline1\n\nline2\n```\n\n结尾"
        body, line_to_block = self.engine.convert_with_anchors(text)
        # 应产生 3 个锚点（开头、代码块、结尾）
        assert '<a id="md-b-0"' in body
        assert '<a id="md-b-1"' in body
        assert '<a id="md-b-2"' in body
        # 验证代码块内部行归属于同一块
        assert line_to_block[2] == 1  # "开头"在块0，"```" 在块1
        assert line_to_block[4] == 1  # 代码块内空行也归属块1
        assert line_to_block[5] == 1  # "line2" 也在块1

    def test_convert_with_anchors_empty_line_mapping(self):
        """空行应映射到最近的上一非空块。"""
        text = "# 标题\n\n\n正文"
        body, line_to_block = self.engine.convert_with_anchors(text)
        # 第 1 行是空行，应归属到块 0（标题）
        assert line_to_block[1] == 0
        # 第 3 行是 "正文"，应归属到块 1
        assert line_to_block[3] == 1

    def test_convert_with_anchors_empty_text(self):
        """空文本应返回空映射。"""
        body, line_to_block = self.engine.convert_with_anchors("")
        assert body == ""
        assert line_to_block == {}

    def test_convert_with_anchors_wrapped_html(self):
        """锚点注入后的 body 应可正常被 wrap_html 包装。"""
        text = "# 标题\n\n正文段落"
        body, _ = self.engine.convert_with_anchors(text)
        full = self.engine.wrap_html(body, preview_mode=True)
        assert '<!DOCTYPE html>' in full
        assert '<a id="md-b-0"' in full
        assert '<h1' in full
        assert '</html>' in full


def run_tests():
    """简单的测试运行器（不依赖 pytest）。"""
    test = TestMarkdownEngine()
    test.setup_class()

    methods = [
        m for m in dir(test)
        if m.startswith("test_") and callable(getattr(test, m))
    ]

    passed = 0
    failed = 0
    for method_name in methods:
        try:
            getattr(test, method_name)()
            print(f"  PASS  {method_name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {method_name} - {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {method_name} - {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Result: {passed} passed, {failed} failed ({passed + failed} total)")
    return failed == 0


if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
