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
        """预览模式应包含公式高亮 CSS。"""
        full = self.engine.wrap_html("<p>test</p>", preview_mode=True)
        assert "arithmatex" in full

    def test_wrap_html_export_mode_no_math_css(self):
        """导出模式不应包含公式高亮 CSS。"""
        full = self.engine.wrap_html("<p>test</p>", preview_mode=False)
        assert "arithmatex" not in full


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
