"""
Markdown 源码编辑器 —— 带行号的 QPlainTextEdit 子类。
支持拖放/粘贴图片和文件，自动插入 Markdown 引用链接。
"""

from pathlib import Path
from urllib.parse import urlparse, unquote

from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize, QUrl
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

    # 图片文件扩展名
    IMAGE_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
        ".bmp", ".ico", ".tiff", ".tif", ".apng", ".avif",
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        # 当前 Markdown 文件所在目录（用于计算相对路径）
        self._base_dir: str | None = None

        # 接受拖放
        self.setAcceptDrops(True)

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

    # ── 基础目录（用于相对路径计算） ────────────────────

    def set_base_dir(self, path: str | None) -> None:
        """设置当前 Markdown 文件所在目录。
        拖放/粘贴文件时，若文件在该目录下则使用相对路径。
        """
        self._base_dir = path

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

    # ── 文件/图片拖放与粘贴 ──────────────────────────────

    @staticmethod
    def _is_image_path(filepath: str) -> bool:
        """判断文件路径是否为图片。"""
        return Path(filepath).suffix.lower() in EditorWidget.IMAGE_EXTENSIONS

    def _resolve_path(self, filepath: str) -> str:
        """将绝对路径解析为 Markdown 可用的路径。
        若文件在当前文档目录下则使用相对路径，否则使用绝对路径。
        统一使用正斜杠。
        """
        resolved = str(Path(filepath).resolve())

        if self._base_dir:
            base = str(Path(self._base_dir).resolve())
            try:
                relative = str(Path(resolved).relative_to(base))
                # 统一正斜杠
                return relative.replace("\\", "/")
            except ValueError:
                pass

        return resolved.replace("\\", "/")

    def _insert_file_links(self, paths: list[str]) -> None:
        """在光标位置逐行插入文件的 Markdown 引用链接。"""
        cursor = self.textCursor()
        lines: list[str] = []
        for filepath in paths:
            filename = Path(filepath).name
            link_path = self._resolve_path(filepath)
            if self._is_image_path(filepath):
                lines.append(f"![{filename}]({link_path})")
            else:
                lines.append(f"[{filename}]({link_path})")

        text = ("\n".join(lines) + "\n") if len(lines) > 1 else lines[0]
        cursor.insertText(text)
        self.setTextCursor(cursor)
        self.setFocus()

    # ── 拖放事件 ─────────────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        """接受包含文件 URL 的拖放。"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        """处理文件拖放 —— 插入 Markdown 引用链接。"""
        urls = event.mimeData().urls()
        if urls:
            local_paths: list[str] = []
            for url in urls:
                if url.isLocalFile():
                    local_paths.append(url.toLocalFile())
            if local_paths:
                self._insert_file_links(local_paths)
                return
        super().dropEvent(event)

    # ── 粘贴事件 ─────────────────────────────────────────

    def insertFromMimeData(self, source) -> None:
        """粘贴时优先处理文件 URL，否则交给默认文本粘贴。"""
        if source.hasUrls():
            local_paths: list[str] = []
            for url in source.urls():
                if url.isLocalFile():
                    local_paths.append(url.toLocalFile())
            # 同时有文本和文件时，只处理文件（图片或文件在剪贴板中常有双重表示）
            if local_paths:
                self._insert_file_links(local_paths)
                return
        super().insertFromMimeData(source)


class _LineNumberArea(QWidget):
    """编辑器左侧的行号显示区域。"""

    def __init__(self, editor: EditorWidget):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor._line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.line_number_area_paint_event(event)
