"""
主窗口 —— 组装菜单栏、工具栏、编辑器、预览面板。
"""

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QSplitter,
    QStatusBar,
    QWidget,
)

from ..core.file_manager import FileManager
from ..core.font_manager import (
    FontManager,
    RECOMMENDED_FONTS,
    _FontDownloadWorker,
)
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

        # 字体管理器
        fonts_dir = Path(__file__).resolve().parent.parent / "resources" / "fonts"
        self._font_manager = FontManager(fonts_dir)
        loaded = self._font_manager.load_local_fonts()
        if loaded > 0:
            print(f"[FontManager] 已加载 {loaded} 个本地字体文件")

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

        # ── 字体菜单 ──
        self._setup_font_menu(menubar)

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
            font_css = self._get_font_face_css(preview_mode=False)
            html = self._engine.wrap_html(
                self._engine.convert(self._editor.toPlainText()),
                title=Path(path).stem,
                font_face_css=font_css,
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
            font_css = self._get_font_face_css(preview_mode=True)
            html = self._engine.wrap_html(body, preview_mode=True,
                                          font_face_css=font_css)
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

    # ── 字体管理 ──────────────────────────────────────

    def _get_font_face_css(self, preview_mode: bool) -> str:
        """收集所有可用字体的 @font-face CSS，以及当前激活字体的覆盖规则。"""
        parts = []
        for key, entry in RECOMMENDED_FONTS.items():
            if not self._font_manager.is_usable(key):
                continue
            if preview_mode:
                css = self._font_manager.get_preview_font_face_css(key)
            else:
                css = self._font_manager.get_font_face_css(key)
            if css:
                parts.append(css)
        # 如果选中了某字体，追加一条 body font-family 覆盖
        if self._font_manager.active_font:
            entry = RECOMMENDED_FONTS.get(self._font_manager.active_font)
            if entry and self._font_manager.is_usable(entry.key):
                parts.append(
                    f'body {{ font-family: {entry.css_fallback} !important; }}'
                )
        return "\n".join(parts)

    def _setup_font_menu(self, menubar) -> None:
        """初始化顶层「字体」菜单（与文件/编辑/视图同级）。"""
        font_menu = menubar.addMenu("字体(&F)")
        self._populate_font_menu_actions(font_menu)

    def _populate_font_menu_actions(self, font_menu) -> None:
        """填充字体子菜单项（可重复调用以刷新）。"""
        default_action = QAction("系统默认", self)
        default_action.setCheckable(True)
        default_action.setChecked(self._font_manager.active_font is None)
        default_action.triggered.connect(
            lambda: self._on_font_select(None)
        )
        font_menu.addAction(default_action)
        font_menu.addSeparator()

        for key, entry in RECOMMENDED_FONTS.items():
            available = self._font_manager.is_usable(key)
            action = QAction(entry.description, self)
            action.setCheckable(True)
            action.setChecked(self._font_manager.active_font == key)
            action.setEnabled(available)
            action.triggered.connect(
                lambda checked, k=key: self._on_font_select(k)
            )
            font_menu.addAction(action)

            if not available:
                dl_action = QAction(f"  ⬇ 下载 {entry.family_name}", self)
                dl_action.triggered.connect(
                    lambda checked, k=key: self._on_download_font(k)
                )
                font_menu.addAction(dl_action)

    def _on_font_select(self, key: str | None) -> None:
        """选择当前字体并刷新预览。"""
        self._font_manager.active_font = key
        self._rebuild_font_menu()
        self._update_preview()
        name = RECOMMENDED_FONTS[key].family_name if key else "系统默认"
        self._update_status(f"字体: {name}")

    def _on_download_font(self, key: str) -> None:
        """在后台线程下载字体，显示进度对话框。"""
        entry = RECOMMENDED_FONTS.get(key)
        if entry is None:
            return

        # ── 进度对话框 ──
        progress_dlg = QProgressDialog(
            f"正在下载 {entry.family_name} …", "取消", 0, 100, self,
        )
        progress_dlg.setWindowTitle("字体下载")
        progress_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dlg.setMinimumDuration(0)  # 立即显示
        progress_dlg.setValue(0)

        # ── 工作线程 ──
        thread = QThread(self)
        worker = _FontDownloadWorker(self._font_manager, key)
        worker.moveToThread(thread)

        # 信号连接
        worker.progress.connect(progress_dlg.setValue)

        worker.finished.connect(
            lambda k: self._on_download_done(k, progress_dlg, thread, worker)
        )
        worker.error.connect(
            lambda k, err: self._on_download_error(k, err, entry,
                                                    progress_dlg, thread, worker)
        )

        # 取消按钮：终止线程
        progress_dlg.canceled.connect(thread.quit)

        # 线程结束后清理
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(worker.deleteLater)

        thread.started.connect(worker.run)
        thread.start()

    def _on_download_done(
        self, key: str, dlg: QProgressDialog, thread: QThread,
        worker: _FontDownloadWorker,
    ) -> None:
        """下载完成（主线程回调）。"""
        dlg.setValue(100)
        dlg.close()
        thread.quit()
        thread.wait()
        self._font_manager.load_local_fonts()
        entry = RECOMMENDED_FONTS.get(key)
        name = entry.family_name if entry else key
        self._update_status(f"字体 {name} 下载完成")
        self._rebuild_font_menu()
        self._update_preview()
        QMessageBox.information(self, "下载完成",
                                f"字体「{name}」已下载并安装。")

    def _on_download_error(
        self, key: str, error: str, entry, dlg: QProgressDialog,
        thread: QThread, worker: _FontDownloadWorker,
    ) -> None:
        """下载出错（主线程回调）。"""
        dlg.close()
        thread.quit()
        thread.wait()
        self._update_status(f"下载失败: {error}")
        QMessageBox.warning(self, "下载失败",
                            f"字体 {entry.family_name} 下载失败:\n{error}")

    def _rebuild_font_menu(self) -> None:
        """重建字体菜单（下载完成后调用）。"""
        # 菜单栏顺序: 文件(0), 编辑(1), 视图(2), 字体(3)
        font_menu = self.menuBar().actions()[3].menu()
        font_menu.clear()
        self._populate_font_menu_actions(font_menu)

    # ── 主题切换 ──────────────────────────────────────

    def _apply_theme(self, theme_name: str) -> None:
        """切换到指定主题。"""
        theme = THEMES.get(theme_name)
        if theme is None:
            return

        self._current_theme = theme_name
        QApplication.instance().setStyleSheet(theme.qss)
        self._engine.theme = theme.engine_theme

        # 同步行号区域颜色
        if "暗色" in theme_name:
            self._editor.set_line_number_colors("#1e1e1e", "#777")
        else:
            self._editor.set_line_number_colors("#f0f0f0", "#999")

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
