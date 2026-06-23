"""
编辑器标签页 —— 封装单个文件的编辑器 + 预览面板 + 文件管理器。
"""

import time as _time

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QSplitter, QWidget

from ..core.file_manager import FileManager
from .editor_widget import EditorWidget
from .preview_widget import PreviewWidget


class Tab(QWidget):
    """单个标签页：包含 FileManager + EditorWidget + PreviewWidget + QSplitter。"""

    text_changed = pyqtSignal()                # 编辑器内容变化 → MainWindow 启动防抖
    markdown_file_dropped = pyqtSignal(str)    # 拖入 .md 文件 → MainWindow 打开

    def __init__(self, parent=None):
        super().__init__(parent)

        self._file_manager = FileManager()

        # ── 自动保存追踪 ──────────────────────────────
        self._chars_since_save: int = 0          # 自上次保存后累计键盘活动次数
        self._last_save_time: float = _time.time()  # 上次保存的时间戳

        # ── 编辑器 + 预览 ──────────────────────────────
        self._editor = EditorWidget()
        self._preview = PreviewWidget()

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._editor)
        self._splitter.addWidget(self._preview)
        self._splitter.setSizes([600, 600])

        # ── 布局 ──────────────────────────────────────
        from PyQt6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)

        # ── 同步滚动 ──────────────────────────────────
        self._sync_scrolling: bool = True
        self._syncing: bool = False

        editor_sb = self._editor.verticalScrollBar()
        preview_sb = self._preview.verticalScrollBar()
        editor_sb.valueChanged.connect(
            lambda v: self._on_editor_scrolled(v, editor_sb, preview_sb))
        preview_sb.valueChanged.connect(
            lambda v: self._on_preview_scrolled(v, editor_sb, preview_sb))

        # ── 信号转发 ──────────────────────────────────
        self._editor.textChanged.connect(self._on_text_changed)
        self._editor.markdown_file_dropped.connect(self.markdown_file_dropped.emit)

    def _on_text_changed(self) -> None:
        """编辑器内容变化时累加计数器并转发信号。"""
        self._chars_since_save += 1
        self.text_changed.emit()

    # ── 同步滚动 ──────────────────────────────────────

    def set_sync_scrolling(self, enabled: bool) -> None:
        """启用或禁用编辑区与预览区的同步滚动。"""
        self._sync_scrolling = enabled

    def _on_editor_scrolled(self, value: int, editor_sb, preview_sb) -> None:
        """编辑器滚动 → 按比例同步到预览区。"""
        if self._syncing or not self._sync_scrolling:
            return
        self._syncing = True
        ratio = value / max(editor_sb.maximum(), 1)
        preview_sb.setValue(int(ratio * preview_sb.maximum()))
        self._syncing = False

    def _on_preview_scrolled(self, value: int, editor_sb, preview_sb) -> None:
        """预览区滚动 → 按比例同步到编辑器。"""
        if self._syncing or not self._sync_scrolling:
            return
        self._syncing = True
        ratio = value / max(preview_sb.maximum(), 1)
        editor_sb.setValue(int(ratio * editor_sb.maximum()))
        self._syncing = False

    # ── 属性 ──────────────────────────────────────────

    @property
    def modified(self) -> bool:
        return self._file_manager.modified

    @property
    def filename(self) -> str:
        return self._file_manager.filename

    @property
    def current_path(self) -> str | None:
        return self._file_manager.current_path

    @property
    def editor_text(self) -> str:
        return self._editor.toPlainText()

    @property
    def file_manager(self) -> FileManager:
        return self._file_manager

    @property
    def editor(self) -> EditorWidget:
        return self._editor

    @property
    def preview(self) -> PreviewWidget:
        return self._preview

    @property
    def splitter(self) -> QSplitter:
        return self._splitter

    # ── 便捷方法 ──────────────────────────────────────

    def set_plain_text(self, text: str) -> None:
        """设置编辑器内容并重置修改标记（用于加载文件）。"""
        was_modified = self._file_manager.modified
        self._editor.setPlainText(text)
        if not was_modified:
            self._file_manager._modified = False

    def set_base_dir(self, path: str | None) -> None:
        """设置基础目录（用于相对路径解析）。"""
        self._editor.set_base_dir(path)

    # ── 自动保存 ──────────────────────────────────────

    def mark_saved(self) -> None:
        """保存成功后重置自动保存追踪状态。"""
        self._chars_since_save = 0
        self._last_save_time = _time.time()

    def should_auto_save(self) -> bool:
        """判断是否满足自动保存条件。

        条件（全部满足）：
        1. 有已保存的路径（不自动保存「未命名」新文件）
        2. 处于修改状态
        3. 内容非空
        4. 编辑量 > 300 次键盘活动 或 距上次保存 > 15 分钟
        """
        if not self.current_path or not self.modified:
            return False
        if not self.editor_text.strip():
            return False
        elapsed = _time.time() - self._last_save_time
        return self._chars_since_save > 300 or elapsed > 900

    # ── 状态快照 ──────────────────────────────────────

    def memento(self) -> dict:
        """保存标签页状态快照，用于缓存已渲染的预览。"""
        return {
            "text": self.editor_text,
            "path": self.current_path,
            "filename": self.filename,
        }
