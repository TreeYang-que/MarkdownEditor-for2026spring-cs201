"""
Markdown 预览面板 —— 使用 QTextBrowser 实时渲染 HTML。
"""

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWidgets import QTextBrowser


class PreviewWidget(QTextBrowser):
    """HTML 实时预览面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        # 默认显示提示文字
        self.setPlaceholderText("预览区域 — 在左侧输入 Markdown 即可实时预览")

    def show_preview(self, html: str) -> None:
        """显示渲染后的 HTML，保持原来的滚动位置。

        Args:
            html: 完整的 HTML 文档字符串。
        """
        sb = self.verticalScrollBar()
        saved_value = sb.value()

        self.setHtml(html)

        # 恢复绝对滚动位置，不超过新的最大值
        sb.setValue(min(saved_value, sb.maximum()))

    def show_placeholder(self) -> None:
        """显示占位提示。"""
        self.clear()
        self.setPlaceholderText("预览区域 — 在左侧输入 Markdown 即可实时预览")
