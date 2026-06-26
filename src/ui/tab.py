"""
编辑器标签页 —— 封装单个文件的编辑器 + 预览面板 + 文件管理器。
"""

import time as _time

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
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

        # ── 块级锚点同步映射 ───────────────────────────
        self._line_to_block: dict[int, int] = {}  # 编辑区行号 → 逻辑块索引
        self._block_to_first_line: dict[int, int] = {}  # 块索引 → 该块首行
        self._block_to_last_line: dict[int, int] = {}   # 块索引 → 该块末行
        self._anchor_positions: list[tuple[int, int]] = []  # [(preview_y, block_idx), ...]
        self._anchor_y_lookup: dict[int, int] = {}  # block_idx → preview_y
        self._block_next_anchor_y: dict[int, int | None] = {}  # block_idx → 下一块的 anchor_y

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

        # 节流定时器：高频滚动时（如触控板）将同步限制在 ~60fps
        self._forward_throttle = QTimer(self)
        self._forward_throttle.setSingleShot(True)
        self._forward_throttle.setInterval(16)
        self._forward_throttle.timeout.connect(self._flush_forward_sync)
        self._reverse_throttle = QTimer(self)
        self._reverse_throttle.setSingleShot(True)
        self._reverse_throttle.setInterval(16)
        self._reverse_throttle.timeout.connect(self._flush_reverse_sync)
        self._pending_forward: tuple | None = None
        self._pending_reverse: tuple | None = None
        self._forward_driven: bool = False  # 预览滚动是否由正向同步触发

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
        if not enabled:
            self._forward_throttle.stop()
            self._reverse_throttle.stop()
            self._pending_forward = None
            self._pending_reverse = None
            self._forward_driven = False

    def refresh_sync(self) -> None:
        """外部调用：用当前编辑区可见首行 + 最新锚点映射，立即重算预览位置。

        用于窗口 resize 后锚点坐标已更新的场景——不做节流，直接完成同步。
        """
        if not self._sync_scrolling or not self._line_to_block:
            return
        editor_sb = self._editor.verticalScrollBar()
        preview_sb = self._preview.verticalScrollBar()
        self._pending_forward = (editor_sb.value(), editor_sb, preview_sb)
        self._do_forward_sync()
        self._pending_forward = None

    def set_line_block_map(self, mapping: dict[int, int]) -> None:
        """由 MainWindow 在预览更新后调用，存储行→块映射表。

        同时构建反向索引：块索引 → 该块的首行 / 末行，
        用于预览→编辑区的锚点反向同步。
        """
        self._line_to_block = mapping
        # 构建反向索引
        self._block_to_first_line.clear()
        self._block_to_last_line.clear()
        if not mapping:
            return
        for line, blk in sorted(mapping.items()):
            if blk not in self._block_to_first_line:
                self._block_to_first_line[blk] = line
            self._block_to_last_line[blk] = line  # 最后一个即为末行

    def set_anchor_map(self, positions: list[tuple[int, int]]) -> None:
        """设置预览区锚点 Y 坐标映射（由 MainWindow 在 setHtml 后调用）。

        同时预计算每个块的下一锚点 Y，用于正向/反向同步的块高度插值。

        Args:
            positions: [(preview_y, block_index), ...]，按 Y 升序排列。
        """
        self._anchor_positions = positions
        self._anchor_y_lookup = {idx: y for y, idx in positions}
        # 预计算每个块的下一锚点 Y（最后一块为 None，运行时用文档底部代替）
        self._block_next_anchor_y.clear()
        for i, (y, idx) in enumerate(positions):
            self._block_next_anchor_y[idx] = (
                positions[i + 1][0] if i + 1 < len(positions) else None
            )

    # ── 同步滚动架构 ──────────────────────────────────
    #
    #  _forward_driven 标志消除正向同步触发的反馈回环：
    #
    #  用户滚轮/拖编辑区滚动条
    #    → _on_editor_scrolled → _do_forward_sync
    #    → 设 _forward_driven=True → preview_sb.setValue()
    #    → _on_preview_scrolled → _do_reverse_sync
    #    → 检测 _forward_driven → 丢弃（不移动编辑区）
    #
    #  用户直接滚轮/拖预览区滚动条
    #    → _on_preview_scrolled → _do_reverse_sync
    #    → _forward_driven=False → _syncing=True
    #    → editor_sb.setValue() → 编辑区跟随预览区

    # ── 正向同步：编辑 → 预览 ──────────────────────────

    def _on_editor_scrolled(self, value: int, editor_sb, preview_sb) -> None:
        """编辑区滚动 → 节流后翻译为预览区滚动操作。"""
        if self._syncing or not self._sync_scrolling:
            return
        if not self._line_to_block:
            return

        self._pending_forward = (value, editor_sb, preview_sb)
        if not self._forward_throttle.isActive():
            self._forward_throttle.start()

    def _flush_forward_sync(self) -> None:
        """节流定时器触发：用最新待处理值完成正向同步。"""
        if self._pending_forward is not None:
            self._do_forward_sync()
            self._pending_forward = None

    def _do_forward_sync(self) -> None:
        """根据编辑区可见行计算预览目标 Y 并设置预览滚动条。

        设 _forward_driven=True 使得后续反向同步跳过编辑区定位，
        避免与用户当前在编辑区的操作（滚轮/拖滚动条）冲突产生抽搐。
        """
        _value, editor_sb, preview_sb = self._pending_forward

        first_visible = self._editor.firstVisibleBlock()
        if not first_visible.isValid():
            return

        line_num = first_visible.blockNumber()
        block_idx = self._line_to_block.get(line_num, 0)

        if self._anchor_y_lookup and self._block_to_first_line:
            start_line = self._block_to_first_line.get(block_idx, 0)
            end_line = self._block_to_last_line.get(block_idx, start_line)
            line_range = max(end_line - start_line, 1)
            inner_ratio = (line_num - start_line) / line_range

            anchor_y = self._anchor_y_lookup.get(block_idx, 0)
            next_y = self._block_next_anchor_y.get(block_idx)
            if next_y is not None:
                block_height = max(next_y - anchor_y, 1)
            else:
                # scrollbar.maximum() = document_height - viewport_height，
                # 必须加上 pageStep() 才等于真正的文档底部坐标。
                doc_bottom = preview_sb.maximum() + preview_sb.pageStep()
                block_height = max(doc_bottom - anchor_y, 1)

            target_y = int(anchor_y + inner_ratio * block_height)
        else:
            ratio = _value / max(editor_sb.maximum(), 1)
            target_y = int(ratio * preview_sb.maximum())

        # 标记此预览滚动由正向同步触发，反向同步将跳过编辑区定位
        self._forward_driven = True
        preview_sb.setValue(target_y)

    # ── 反向同步：预览 → 编辑 ──────────────────────────

    def _on_preview_scrolled(self, value: int, editor_sb, preview_sb) -> None:
        """预览区滚动 → 节流后通过锚点映射反向定位编辑区。"""
        if self._syncing or not self._sync_scrolling:
            return

        self._pending_reverse = (value, editor_sb, preview_sb)
        if not self._reverse_throttle.isActive():
            self._reverse_throttle.start()

    def _flush_reverse_sync(self) -> None:
        """节流定时器触发：用最新待处理值完成反向同步。"""
        if self._pending_reverse is not None:
            self._do_reverse_sync()
            self._pending_reverse = None

    def _do_reverse_sync(self) -> None:
        """根据预览区滚动位置反向定位编辑区。

        若预览滚动由正向同步触发（_forward_driven=True），
        跳过编辑区定位，避免与用户正在进行的编辑区操作冲突。
        """
        value, editor_sb, preview_sb = self._pending_reverse

        # 正向同步驱动的预览滚动：编辑区已在用户操作的位置，
        # 无需反向校正（校正会导致"抽搐回退"）
        if self._forward_driven:
            self._forward_driven = False
            return

        self._syncing = True

        if self._anchor_positions and self._block_to_first_line:
            target_block = 0
            for _y, _block_idx in self._anchor_positions:
                if _y <= value:
                    target_block = _block_idx
                else:
                    break

            anchor_y = self._anchor_y_lookup.get(target_block, 0)
            next_y = self._block_next_anchor_y.get(target_block)
            if next_y is None:
                next_y = preview_sb.maximum() + preview_sb.pageStep()

            start_line = self._block_to_first_line.get(target_block, 0)
            end_line = self._block_to_last_line.get(target_block, start_line)

            block_height = max(next_y - anchor_y, 1)
            inner_ratio = max(0.0, min(1.0, (value - anchor_y) / block_height))

            line_range = max(end_line - start_line, 1)
            target_line = start_line + inner_ratio * line_range

            total_lines = max(self._editor.blockCount(), 1)
            editor_sb.setValue(
                int(target_line / max(total_lines - 1, 1) * editor_sb.maximum())
            )
        else:
            ratio = value / max(preview_sb.maximum(), 1)
            editor_sb.setValue(int(ratio * editor_sb.maximum()))

        QTimer.singleShot(0, lambda: setattr(self, '_syncing', False))

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
        # setPlainText 可能触发 viewport palette 重置，确保光标颜色恢复。
        # EditorWidget.setPlainText 重写已做同步+异步恢复，此处再调一次作为保险。
        self._editor._apply_caret_color()
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
