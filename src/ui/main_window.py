"""
主窗口 —— 组装菜单栏、工具栏、编辑器、预览面板。
"""

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QWidget,
)

from ..core.file_manager import FileManager
from ..core.markdown_engine import MarkdownEngine
from ..themes.style import DEFAULT_THEME, THEMES, Theme
from .editor_widget import EditorWidget
from .preview_widget import PreviewWidget
from .toolbar import MarkdownToolbar


class MainWindow(QMainWindow):
    """Markdown 编辑器主窗口。"""

    WINDOW_TITLE = "MarkdownEditor"
    WINDOW_SIZE = (1200, 780)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.WINDOW_TITLE)
        self.resize(*self.WINDOW_SIZE)

        # ── 核心模块 ──────────────────────────────────
        self._engine = MarkdownEngine()
        self._file_manager = FileManager()

        # ── UI 组件 ───────────────────────────────────
        self._editor = EditorWidget()
        self._preview = PreviewWidget()
        self._toolbar = MarkdownToolbar()

        # ── 组装 ──────────────────────────────────────
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()
        self._connect_signals()

        # ── 初始主题 ──────────────────────────────────
        self._current_theme: str = DEFAULT_THEME
        self._apply_theme(DEFAULT_THEME)

        # 预览防抖定时器（300ms）
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(300)
        self._preview_timer.timeout.connect(self._update_preview)

    # ── 菜单栏 ────────────────────────────────────────

    def _setup_menubar(self) -> None:
        menubar = self.menuBar()

        # ── 文件菜单 ──
        file_menu = menubar.addMenu("文件(&F)")

        new_action = QAction("新建(&N)", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)

        open_action = QAction("打开(&O)...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("保存(&S)", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        save_as_action = QAction("另存为(&A)...", self)
        save_as_action.setShortcut(
            QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_S)
        )
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        export_html_action = QAction("导出 HTML(&H)...", self)
        export_html_action.triggered.connect(self._on_export_html)
        file_menu.addAction(export_html_action)

        export_pdf_action = QAction("导出 PDF(&P)...", self)
        export_pdf_action.setEnabled(False)  # 暂未实现
        file_menu.addAction(export_pdf_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Q))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ── 编辑菜单 ──
        edit_menu = menubar.addMenu("编辑(&E)")

        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._editor.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做(&R)", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._editor.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("剪切(&X)", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self._editor.cut)
        edit_menu.addAction(cut_action)

        copy_action = QAction("复制(&C)", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self._editor.copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction("粘贴(&V)", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self._editor.paste)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        select_all_action = QAction("全选(&A)", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self._editor.selectAll)
        edit_menu.addAction(select_all_action)

        # ── 视图菜单 ──
        view_menu = menubar.addMenu("视图(&V)")

        for theme_name in THEMES:
            action = QAction(f"切换{theme_name}主题", self)
            action.triggered.connect(
                lambda checked, t=theme_name: self._apply_theme(t)
            )
            view_menu.addAction(action)

        # ── 帮助菜单 ──
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    # ── 工具栏 ────────────────────────────────────────

    def _setup_toolbar(self) -> None:
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)

    # ── 中央组件 ──────────────────────────────────────

    def _setup_central_widget(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._editor)
        splitter.addWidget(self._preview)
        splitter.setSizes([600, 600])  # 初始 1:1
        self.setCentralWidget(splitter)

    # ── 状态栏 ────────────────────────────────────────

    def _setup_statusbar(self) -> None:
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._update_status("就绪")

    def _update_status(self, message: str) -> None:
        self._status_bar.showMessage(message)

    # ── 信号连接 ──────────────────────────────────────

    def _connect_signals(self) -> None:
        # 编辑内容变化 → 延迟更新预览
        self._editor.textChanged.connect(self._on_text_changed)
        # 工具栏格式化请求
        self._toolbar.format_requested.connect(self._insert_format)

    # ── 文件操作 ──────────────────────────────────────

    def _on_new(self) -> None:
        if self._maybe_save():
            self._editor.clear()
            self._file_manager.new_file()
            self._preview.show_placeholder()
            self.setWindowTitle(self.WINDOW_TITLE)
            self._update_status("新建文件")

    def _on_open(self) -> None:
        if not self._maybe_save():
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "打开 Markdown 文件",
            self._file_manager.current_dir,
            FileManager.MARKDOWN_FILTER,
        )
        if not path:
            return

        try:
            content = self._file_manager.read_file(path)
            self._editor.setPlainText(content)
            self._update_window_title()
            self._update_status(f"已打开: {path}")
        except IOError as e:
            QMessageBox.critical(self, "错误", str(e))

    def _on_save(self) -> None:
        if self._file_manager.current_path:
            self._do_save(self._file_manager.current_path)
        else:
            self._on_save_as()

    def _on_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 Markdown 文件",
            str(Path(self._file_manager.current_dir) / self._file_manager.filename),
            FileManager.MARKDOWN_FILTER,
        )
        if path:
            self._do_save(path)

    def _do_save(self, path: str) -> None:
        try:
            saved = self._file_manager.save_file(self._editor.toPlainText(), path)
            self._update_window_title()
            self._update_status(f"已保存: {saved}")
        except IOError as e:
            QMessageBox.critical(self, "错误", str(e))

    def _on_export_html(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 HTML",
            str(Path(self._file_manager.current_dir) / "export.html"),
            FileManager.HTML_FILTER,
        )
        if not path:
            return

        try:
            html = self._engine.wrap_html(
                self._engine.convert(self._editor.toPlainText()),
                title=Path(path).stem,
            )
            exported = self._file_manager.export_html(html, path)
            self._update_status(f"已导出: {exported}")
        except IOError as e:
            QMessageBox.critical(self, "错误", str(e))

    # ── 预览更新 ──────────────────────────────────────

    def _on_text_changed(self) -> None:
        """编辑器内容变化时（重新）启动防抖定时器。"""
        self._file_manager.mark_modified()
        self._preview_timer.start()

    def _update_preview(self) -> None:
        """执行 Markdown → HTML 转换并更新预览。"""
        text = self._editor.toPlainText()
        if not text.strip():
            self._preview.show_placeholder()
            return

        try:
            body = self._engine.convert(text)
            html = self._engine.wrap_html(body)
            self._preview.show_preview(html)
        except Exception:
            # 解析错误时静默忽略，保持上次预览内容
            pass

    # ── 格式化工具 ────────────────────────────────────

    def _insert_format(self, before: str, after: str) -> None:
        """在光标位置或选中区域包裹 Markdown 格式标记。"""
        cursor = self._editor.textCursor()
        selected = cursor.selectedText()

        if selected:
            cursor.insertText(before + selected + after)
        else:
            cursor.insertText(before + after)
            # 光标移到标记中间
            cursor.movePosition(
                cursor.MoveOperation.Left,
                cursor.MoveMode.MoveAnchor,
                len(after),
            )
        self._editor.setTextCursor(cursor)
        self._editor.setFocus()

    # ── 主题切换 ──────────────────────────────────────

    def _apply_theme(self, theme_name: str) -> None:
        """切换到指定主题。"""
        theme = THEMES.get(theme_name)
        if theme is None:
            return

        self._current_theme = theme_name
        QApplication.instance().setStyleSheet(theme.qss)
        self._update_preview()

        # 菜单中标记当前主题（切换后取消前一个的勾选）
        view_menu = self.menuBar().actions()[2]  # 视图菜单
        for action in view_menu.menu().actions():
            action.setCheckable(True)
            action.setChecked(theme_name in action.text())

        self._update_status(f"主题: {theme_name}")

    # ── 辅助方法 ──────────────────────────────────────

    def _maybe_save(self) -> bool:
        """如果有未保存的修改，询问用户是否保存。返回 False 表示取消。"""
        if not self._file_manager.modified:
            return True

        result = QMessageBox.question(
            self, "未保存的修改",
            "当前文件有未保存的修改，是否保存？",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if result == QMessageBox.StandardButton.Save:
            self._on_save()
            return self._file_manager.current_path is not None
        elif result == QMessageBox.StandardButton.Discard:
            return True
        return False  # Cancel

    def _update_window_title(self) -> None:
        """更新窗口标题显示当前文件名。"""
        title = f"{self._file_manager.filename} - {self.WINDOW_TITLE}"
        self.setWindowTitle(title)

    def _on_about(self) -> None:
        QMessageBox.about(
            self, "关于 MarkdownEditor",
            "<h3>MarkdownEditor</h3>"
            "<p>基于 PyQt6 的 Markdown 桌面编辑器</p>"
            "<p>2026 春季 CS201 课程项目</p>"
            "<hr>"
            "<p>技术栈: Python + PyQt6 + Markdown + Pygments</p>",
        )

    def closeEvent(self, event) -> None:
        """关闭窗口前检查未保存内容。"""
        if self._maybe_save():
            event.accept()
        else:
            event.ignore()
