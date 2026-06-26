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

    def build_anchor_map(self) -> list[tuple[int, int]]:
        """扫描文档中所有 md-b-N 锚点，返回 (y, block_index) 位置列表。

        遍历 QTextDocument 文本片段，寻找锚点格式（isAnchor=True、
        anchorNames 中以 "md-b-" 开头），通过 QTextBlock 的布局矩形获取
        文档坐标系下的 Y 位置。

        Returns:
            [(y_position, block_index), ...] 按 Y 坐标升序排列。
            若文档为空或无锚点则返回空列表。
        """
        doc = self.document()
        if doc.isEmpty():
            return []

        positions: dict[int, int] = {}  # block_index → y_position
        layout = doc.documentLayout()
        block = doc.begin()

        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid():
                    fmt = fragment.charFormat()
                    if fmt.isAnchor():
                        for name in fmt.anchorNames():
                            if name.startswith("md-b-"):
                                try:
                                    block_idx = int(name.split("-")[-1])
                                    if block_idx not in positions:
                                        rect = layout.blockBoundingRect(block)
                                        positions[block_idx] = int(rect.top())
                                except ValueError:
                                    pass
                it += 1
            block = block.next()

        # 按 Y 坐标升序排列，返回 [(y, block_index), ...]
        result = [(y, idx) for idx, y in positions.items()]
        result.sort(key=lambda pair: pair[0])
        return result
