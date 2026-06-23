"""
格式化工具栏 —— 快捷插入 Markdown 语法。
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QToolBar, QToolButton


class MarkdownToolbar(QToolBar):
    """Markdown 格式化工具栏。"""

    # 格式化信号，携带要插入的 Markdown 语法标记
    format_requested = pyqtSignal(str, str)  # (before, after) 包裹光标选区的标记

    # ── 按钮定义 ──────────────────────────────────────

    BUTTONS: list[dict] = [
        {"text": "粗体", "before": "**", "after": "**", "tip": "粗体 (Ctrl+B)"},
        {"text": "斜体", "before": "*",  "after": "*",  "tip": "斜体 (Ctrl+I)"},
        {"text": "删除线", "before": "~~", "after": "~~", "tip": "删除线"},
        None,  # 分隔线
        {"text": "H1", "before": "# ",       "after": "",   "tip": "一级标题"},
        {"text": "H2", "before": "## ",      "after": "",   "tip": "二级标题"},
        {"text": "H3", "before": "### ",     "after": "",   "tip": "三级标题"},
        None,
        {"text": "列表", "before": "- ",      "after": "",   "tip": "无序列表"},
        {"text": "编号", "before": "1. ",     "after": "",   "tip": "有序列表"},
        {"text": "任务", "before": "- [ ] ",  "after": "",   "tip": "任务列表"},
        None,
        {"text": "链接", "before": "[",       "after": "](url)",   "tip": "插入链接"},
        {"text": "图片", "before": "![alt](", "after": ")",        "tip": "插入图片"},
        {"text": "代码", "before": "`",       "after": "`",        "tip": "行内代码"},
        {"text": "代码块", "before": "\n```\n", "after": "\n```\n", "tip": "代码块"},
        None,
        {"text": "引用", "before": "> ",      "after": "",   "tip": "引用"},
        {"text": "分隔线", "before": "\n---\n", "after": "",  "tip": "水平分隔线"},
        None,
        {"text": "行内公式", "before": "$",    "after": "$",      "tip": "行内 LaTeX 公式"},
        {"text": "块级公式", "before": "\n$$\n", "after": "\n$$\n", "tip": "块级 LaTeX 公式"},
    ]

    def __init__(self, parent=None):
        super().__init__("格式化", parent)
        self.setMovable(False)
        self._setup_buttons()

    def _setup_buttons(self) -> None:
        """按 BUTTONS 定义创建工具栏按钮。"""
        for item in self.BUTTONS:
            if item is None:
                self.addSeparator()
                continue

            btn = QToolButton(self)
            btn.setText(item["text"])
            btn.setToolTip(item.get("tip", ""))
            # 捕获 before/after 值避免闭包问题
            before, after = item["before"], item["after"]
            btn.clicked.connect(
                lambda checked, b=before, a=after: self.format_requested.emit(b, a)
            )
            self.addWidget(btn)
