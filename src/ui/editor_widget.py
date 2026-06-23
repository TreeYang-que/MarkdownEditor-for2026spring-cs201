"""
Markdown 源码编辑器 —— 带行号的 QPlainTextEdit 子类。
"""

from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QFontInfo, QPainter, QTextCursor, QTextFormat
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

# 跨平台等宽字体优先级列表
_FALLBACK_FONTS = [
    "Cascadia Code",       # Windows 现代编程字体
    "JetBrains Mono",      # 跨平台编程字体
    "Fira Code",           # 开源编程字体
    "Consolas",            # Windows 经典
    "Courier New",         # Windows 备用
    "DejaVu Sans Mono",    # Linux
    "Menlo",               # macOS
    "Monaco",              # macOS 经典
    "monospace",           # 系统最终兜底
]


def _find_available_font(preferred: str, fallbacks: list[str], fixed_pitch: bool = True) -> str:
    """在系统已安装字体中查找第一个可用的。

    Args:
        preferred: 首选字体名称。
        fallbacks: 备选字体列表。
        fixed_pitch: 是否要求等宽。

    Returns:
        第一个找到的可用字体名称。
    """
    candidates = [preferred] + [f for f in fallbacks if f != preferred]
    for name in candidates:
        font = QFont(name)
        info = QFontInfo(font)
        # 检查字体是否真实可用（Qt 会做字体替换，比较解析后的名称）
        if info.family().lower() == name.lower():
            if not fixed_pitch or info.fixedPitch():
                return name
    # 最终兜底
    return "monospace" if fixed_pitch else font.defaultFamily()


class EditorWidget(QPlainTextEdit):
    """支持行号显示的 Markdown 源码编辑器。"""

    TAB_SPACES = 4

    def __init__(self, parent=None):
        super().__init__(parent)

        # 字体设置 —— 跨平台 fallback
        editor_font = _find_available_font(
            "Cascadia Code", _FALLBACK_FONTS, fixed_pitch=True
        )
        font = QFont(editor_font, 13)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(" ") * self.TAB_SPACES
        )

        # 行号区域
        self._line_number_area = _LineNumberArea(self)

        # 信号连接
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)

        self._update_line_number_area_width(0)

    # ── 行号区域 ──────────────────────────────────────

    def _line_number_area_width(self) -> int:
        """计算行号区域宽度。"""
        digits = max(3, len(str(self.blockCount())))
        # 每数字宽度 + 左右边距
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits + 10

    def _update_line_number_area_width(self, _new_block_count: int) -> None:
        """行数变化时调整边距。"""
        self.setViewportMargins(self._line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        """滚动/更新时重绘行号区域。"""
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(
                cr.left(),
                cr.top(),
                self._line_number_area_width(),
                cr.height(),
            )
        )

    def line_number_area_paint_event(self, event) -> None:
        """绘制行号。"""
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#f0f0f0"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset())
            .top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#999"))
                painter.drawText(
                    0, top,
                    self._line_number_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

        painter.end()

    # ── Tab 键处理 ────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        """Tab 键插入空格。"""
        if event.key() == Qt.Key.Key_Tab:
            cursor = self.textCursor()
            if cursor.hasSelection():
                # 对选中行缩进
                self._indent_selection(cursor)
            else:
                cursor.insertText(" " * self.TAB_SPACES)
            return
        super().keyPressEvent(event)

    def _indent_selection(self, cursor: QTextCursor) -> None:
        """对选中区域的每一行增加缩进。"""
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        while cursor.position() < end:
            cursor.insertText(" " * self.TAB_SPACES)
            end += self.TAB_SPACES
            if not cursor.movePosition(QTextCursor.MoveOperation.Down):
                break


class _LineNumberArea(QWidget):
    """编辑器左侧的行号显示区域。"""

    def __init__(self, editor: EditorWidget):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor._line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.line_number_area_paint_event(event)
