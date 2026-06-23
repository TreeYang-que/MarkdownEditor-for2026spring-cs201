"""
主窗口 —— 组装菜单栏、工具栏、标签页、预览面板。
"""

from pathlib import Path

from PyQt6.QtCore import Qt, QSettings, QTimer, QThread, QObject, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QStatusBar,
    QTabWidget,
)

from ..core.file_manager import FileManager
from ..core.font_manager import (
    FontManager,
    RECOMMENDED_FONTS,
    _FontDownloadWorker,
)
from ..core.markdown_engine import MarkdownEngine
from ..themes.style import DEFAULT_THEME, THEMES
from .tab import Tab
from .toolbar import MarkdownToolbar


class _PreviewWorker(QObject):
    """后台线程：执行 Markdown → HTML 转换，释放主线程 UI。"""

    _do_convert = pyqtSignal(str, int, str, bool)  # text, request_id, font_css, dark_mode
    finished = pyqtSignal(str, int)

    def __init__(self, engine: MarkdownEngine):
        super().__init__()
        self._engine = engine
        self._do_convert.connect(self._on_convert)

    def _on_convert(self, text: str, request_id: int, font_css: str,
                    dark_mode: bool) -> None:
        if not text.strip():
            self.finished.emit("", request_id)
            return
        try:
            body = self._engine.convert(text)
            html = self._engine.wrap_html(body, preview_mode=True,
                                          font_face_css=font_css,
                                          dark_mode=dark_mode)
            self.finished.emit(html, request_id)
        except Exception:
            self.finished.emit("", request_id)

    def request(self, text: str, request_id: int, font_css: str = "",
                dark_mode: bool = False) -> None:
        self._do_convert.emit(text, request_id, font_css, dark_mode)


class MainWindow(QMainWindow):
    """Markdown 编辑器主窗口。"""

    WINDOW_TITLE = "MarkdownEditor"
    WINDOW_SIZE = (1200, 780)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.WINDOW_TITLE)
        self.resize(*self.WINDOW_SIZE)

        # ── 核心模块（所有标签页共享） ──────────────────
        self._engine = MarkdownEngine()

        # 字体管理器
        fonts_dir = Path(__file__).resolve().parent.parent / "resources" / "fonts"
        self._font_manager = FontManager(fonts_dir)
        loaded = self._font_manager.load_local_fonts()
        if loaded > 0:
            print(f"[FontManager] 已加载 {loaded} 个本地字体文件")

        # ── UI 组件 ───────────────────────────────────
        self._toolbar = MarkdownToolbar()
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._active_tab: Tab | None = None

        # ── 组装 ──────────────────────────────────────
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()
        self._connect_signals()

        # ── 后台预览线程 ──────────────────────────────
        self._preview_thread = QThread(self)
        self._preview_worker = _PreviewWorker(self._engine)
        self._preview_worker.moveToThread(self._preview_thread)
        self._preview_worker.finished.connect(self._on_preview_ready)
        self._preview_thread.start()

        # ── 初始主题 ──────────────────────────────────
        self._current_theme: str = DEFAULT_THEME
        self._dark_mode: bool = False
        self._sync_scrolling_enabled: bool = True
        self._cursor_position_enabled: bool = False  # 与同步滚动互斥
        self._caret_color: str = "#222222"  # 由 _apply_theme 更新
        self._apply_theme(DEFAULT_THEME)

        # 预览防抖定时器（间隔按当前模式动态调整）
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)

        # 转换请求计数器（用于丢弃过期结果）
        self._preview_request_id: int = 0

        # ── 自动保存定时器（60 秒间隔） ────────────────
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(60_000)
        self._autosave_timer.timeout.connect(self._autosave_tick)
        self._autosave_timer.start()

        # ── 创建初始空白标签页 ────────────────────────
        self._on_new()

        # ── 初始化后异步任务 ──────────────────────────
        QTimer.singleShot(0, self._restore_settings)
        QTimer.singleShot(100, self._process_pending_files)
        QTimer.singleShot(200, self._check_first_launch)

    # ═══════════════════════════════════════════════════════
    #  菜单栏
    # ═══════════════════════════════════════════════════════

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

        close_tab_action = QAction("关闭标签页(&W)", self)
        close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        close_tab_action.triggered.connect(
            lambda: self._on_tab_close_request(self._tab_widget.currentIndex())
        )
        file_menu.addAction(close_tab_action)

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

        # ── 编辑菜单（动态委托给 active tab） ──
        edit_menu = menubar.addMenu("编辑(&E)")

        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(lambda: self._edit_action("undo"))
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做(&R)", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(lambda: self._edit_action("redo"))
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("剪切(&X)", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(lambda: self._edit_action("cut"))
        edit_menu.addAction(cut_action)

        copy_action = QAction("复制(&C)", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(lambda: self._edit_action("copy"))
        edit_menu.addAction(copy_action)

        paste_action = QAction("粘贴(&V)", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(lambda: self._edit_action("paste"))
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        select_all_action = QAction("全选(&A)", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(lambda: self._edit_action("selectAll"))
        edit_menu.addAction(select_all_action)

        # ── 视图菜单 ──
        view_menu = menubar.addMenu("视图(&V)")

        self._sync_scroll_action = QAction("同步滚动(&Y)", self)
        self._sync_scroll_action.setCheckable(True)
        self._sync_scroll_action.setChecked(True)
        self._sync_scroll_action.triggered.connect(self._on_toggle_sync_scroll)
        view_menu.addAction(self._sync_scroll_action)

        self._cursor_pos_action = QAction("光标定位(&C)", self)
        self._cursor_pos_action.setCheckable(True)
        self._cursor_pos_action.setChecked(False)
        self._cursor_pos_action.triggered.connect(self._on_toggle_cursor_position)
        view_menu.addAction(self._cursor_pos_action)

        view_menu.addSeparator()

        for theme_name in THEMES:
            action = QAction(f"切换{theme_name}主题", self)
            action.setData(theme_name)  # 存 key，供 _apply_theme 精确匹配
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

    # ═══════════════════════════════════════════════════════
    #  工具栏
    # ═══════════════════════════════════════════════════════

    def _setup_toolbar(self) -> None:
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)

    # ═══════════════════════════════════════════════════════
    #  中央组件
    # ═══════════════════════════════════════════════════════

    def _setup_central_widget(self) -> None:
        self.setCentralWidget(self._tab_widget)

    # ═══════════════════════════════════════════════════════
    #  状态栏
    # ═══════════════════════════════════════════════════════

    def _setup_statusbar(self) -> None:
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._update_status("就绪")

    def _update_status(self, message: str) -> None:
        self._status_bar.showMessage(message)

    # ═══════════════════════════════════════════════════════
    #  信号连接
    # ═══════════════════════════════════════════════════════

    def _connect_signals(self) -> None:
        # 工具栏格式化请求 → 动态路由到 active tab
        self._toolbar.format_requested.connect(self._insert_format)
        # 标签页切换
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        self._tab_widget.tabCloseRequested.connect(self._on_tab_close_request)
        # 格式化快捷键绑定
        self._setup_format_shortcuts()

    def _connect_tab_signals(self, tab: Tab) -> None:
        """连接单个标签页的信号。"""
        tab.text_changed.connect(self._on_text_changed)
        tab.markdown_file_dropped.connect(self._on_drop_markdown_file)
        tab.editor.cursorPositionChanged.connect(self._on_cursor_changed)

    # ═══════════════════════════════════════════════════════
    #  格式化快捷键
    # ═══════════════════════════════════════════════════════

    def _setup_format_shortcuts(self) -> None:
        """为工具栏格式化按钮绑定键盘快捷键。"""
        for item in self._toolbar.BUTTONS:
            if item is None:
                continue
            shortcut_str = item.get("shortcut")
            if shortcut_str is None:
                continue
            before, after = item["before"], item["after"]
            shortcut = QShortcut(QKeySequence(shortcut_str), self)
            shortcut.activated.connect(
                lambda b=before, a=after: self._insert_format(b, a)
            )

    # ═══════════════════════════════════════════════════════
    #  编辑操作（动态委托给 active tab）
    # ═══════════════════════════════════════════════════════

    def _edit_action(self, action: str) -> None:
        """将编辑菜单操作委托给当前活动标签页的编辑器。"""
        if self._active_tab is not None:
            getattr(self._active_tab.editor, action)()

    # ═══════════════════════════════════════════════════════
    #  标签页管理
    # ═══════════════════════════════════════════════════════

    def _add_tab(self, tab: Tab, title: str = "未命名", switch: bool = True) -> int:
        """添加标签页并连接信号，同时应用当前主题的行号/光标颜色。"""
        tab.set_sync_scrolling(self._sync_scrolling_enabled)
        if "暗色" in self._current_theme:
            self._apply_cursor_settings_to_tab(tab, "#1e1e1e", "#777")
        else:
            self._apply_cursor_settings_to_tab(tab, "#f0f0f0", "#999")
        self._connect_tab_signals(tab)
        idx = self._tab_widget.addTab(tab, title)
        if switch:
            self._tab_widget.setCurrentIndex(idx)
        return idx

    def _is_tab_empty(self, tab: Tab) -> bool:
        """判断标签页是否为空白未修改状态。"""
        return not tab.editor_text.strip() and not tab.modified

    def _on_tab_changed(self, index: int) -> None:
        """标签页切换时更新状态。"""
        tab = self._tab_widget.widget(index) if index >= 0 else None
        self._active_tab = tab
        if tab is not None:
            self._update_window_title()
            self._update_preview()
            tab.editor.setFocus()
        else:
            self.setWindowTitle(self.WINDOW_TITLE)
            self._update_status("就绪")

    def _on_tab_close_request(self, index: int) -> None:
        """关闭标签页（含保存提示）。"""
        tab = self._tab_widget.widget(index)
        if tab is None:
            return
        if not self._maybe_save_tab(tab):
            return  # 用户取消

        # 断开信号
        try:
            tab.text_changed.disconnect(self._on_text_changed)
        except TypeError:
            pass
        try:
            tab.markdown_file_dropped.disconnect(self._on_drop_markdown_file)
        except TypeError:
            pass

        self._tab_widget.removeTab(index)

        # 无标签页时自动创建空白页
        if self._tab_widget.count() == 0:
            self._on_new()

    def _update_tab_title(self, index: int, tab: Tab) -> None:
        """更新单个标签页的标题（modified 时加 * 前缀）。"""
        prefix = "* " if tab.modified else ""
        self._tab_widget.setTabText(index, f"{prefix}{tab.filename}")

    def _update_all_tab_titles(self) -> None:
        """遍历所有标签页更新标题。"""
        for i in range(self._tab_widget.count()):
            tab = self._tab_widget.widget(i)
            if isinstance(tab, Tab):
                self._update_tab_title(i, tab)

    # ═══════════════════════════════════════════════════════
    #  文件操作
    # ═══════════════════════════════════════════════════════

    def _on_new(self) -> None:
        """新建空白标签页。"""
        tab = Tab()
        self._add_tab(tab, "未命名")
        self.setWindowTitle(self.WINDOW_TITLE)
        self._update_status("新建文件")

    def _on_open(self) -> None:
        """打开 Markdown 文件。当前标签页为空→替换，有内容→新建。"""
        path, _ = QFileDialog.getOpenFileName(
            self, "打开 Markdown 文件",
            (self._active_tab.file_manager.current_dir
             if self._active_tab else str(Path.home())),
            FileManager.MARKDOWN_FILTER,
        )
        if not path:
            return

        # 如果当前标签页为空且未修改，原地打开；否则新建标签页
        tab = self._active_tab
        if tab is not None and self._is_tab_empty(tab):
            self._open_file_in_tab(path, tab)
        else:
            new_tab = Tab()
            self._open_file_in_tab(path, new_tab, switch=False)
            self._add_tab(new_tab, Path(path).name)
            self._update_tab_title(self._tab_widget.currentIndex(), new_tab)

    def _on_drop_markdown_file(self, path: str) -> None:
        """拖入 Markdown 文件 → 打开。"""
        tab = self._active_tab
        if tab is not None and self._is_tab_empty(tab):
            self._open_file_in_tab(path, tab)
        else:
            new_tab = Tab()
            self._open_file_in_tab(path, new_tab, switch=False)
            self._add_tab(new_tab, Path(path).name)
            self._update_tab_title(self._tab_widget.currentIndex(), new_tab)

    def _open_file_in_tab(self, path: str, tab: Tab, switch: bool = True) -> None:
        """在指定标签页中打开文件。"""
        try:
            content = tab.file_manager.read_file(path)
            tab.set_plain_text(content)
            tab.set_base_dir(str(Path(path).parent))
            idx = self._tab_widget.indexOf(tab)
            if idx >= 0:
                self._update_tab_title(idx, tab)
            if switch:
                self._tab_widget.setCurrentWidget(tab)
            self._update_window_title()
            self._update_status(f"已打开: {path}")
        except IOError as e:
            QMessageBox.critical(self, "错误", str(e))

    def _on_save(self) -> None:
        """保存当前文件。"""
        tab = self._active_tab
        if tab is None:
            return
        if tab.current_path:
            self._do_save_tab(tab, tab.current_path)
        else:
            self._on_save_as()

    def _on_save_as(self) -> None:
        """另存为。"""
        tab = self._active_tab
        if tab is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 Markdown 文件",
            str(Path(tab.file_manager.current_dir) / tab.filename),
            FileManager.MARKDOWN_FILTER,
        )
        if path:
            self._do_save_tab(tab, path)

    def _do_save_tab(self, tab: Tab, path: str) -> None:
        """执行保存操作。"""
        try:
            saved = tab.file_manager.save_file(tab.editor_text, path)
            tab.mark_saved()  # 重置自动保存计数器
            tab.set_base_dir(str(Path(saved).parent))
            idx = self._tab_widget.indexOf(tab)
            if idx >= 0:
                self._update_tab_title(idx, tab)
            self._update_window_title()
            self._update_status(f"已保存: {saved}")
        except IOError as e:
            QMessageBox.critical(self, "错误", str(e))

    def _on_export_html(self) -> None:
        """导出当前标签页为 HTML。"""
        tab = self._active_tab
        if tab is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 HTML",
            str(Path(tab.file_manager.current_dir) / "export.html"),
            FileManager.HTML_FILTER,
        )
        if not path:
            return

        try:
            font_css = self._get_font_face_css(preview_mode=False)
            html = self._engine.wrap_html(
                self._engine.convert(tab.editor_text),
                title=Path(path).stem,
                font_face_css=font_css,
            )
            exported = tab.file_manager.export_html(html, path)
            self._update_status(f"已导出: {exported}")
        except IOError as e:
            QMessageBox.critical(self, "错误", str(e))

    # ═══════════════════════════════════════════════════════
    #  保存提示
    # ═══════════════════════════════════════════════════════

    def _maybe_save_tab(self, tab: Tab) -> bool:
        """关闭标签页时处理未保存内容。返回 False 表示取消。

        策略：
        - 有保存路径 → 静默自动保存，不询问
        - 无保存路径（未命名新文件）→ 弹出保存/放弃/取消对话框
        """
        if not tab.modified:
            return True

        # 已有路径 → 自动静默保存
        if tab.current_path:
            try:
                tab.file_manager.save_file(tab.editor_text, tab.current_path)
                tab.mark_saved()
                tab.set_base_dir(str(Path(tab.current_path).parent))
                return True
            except IOError:
                pass  # 自动保存失败 → 降级为手动询问

        # 未命名文件 → 弹出询问框
        result = QMessageBox.question(
            self, "未保存的修改",
            f"「{tab.filename}」有未保存的修改，是否保存？",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if result == QMessageBox.StandardButton.Save:
            self._on_save_as()  # 会弹出保存路径对话框
            return not tab.modified
        elif result == QMessageBox.StandardButton.Discard:
            return True
        return False  # Cancel

    # ═══════════════════════════════════════════════════════
    #  预览更新
    # ═══════════════════════════════════════════════════════

    def _on_text_changed(self) -> None:
        """编辑器内容变化时标记修改并启动防抖定时器。"""
        tab = self.sender()
        if not isinstance(tab, Tab):
            return
        tab.file_manager.mark_modified()
        idx = self._tab_widget.indexOf(tab)
        if idx >= 0:
            self._update_tab_title(idx, tab)
        # 只有活动标签页才更新窗口标题和启动预览
        if tab is self._active_tab:
            self._update_window_title()
            self._start_preview_debounce()

    def _on_cursor_changed(self) -> None:
        """光标位置变化时：若为光标定位模式则启动短防抖更新预览位置。"""
        if not self._cursor_position_enabled:
            return
        tab = self._active_tab
        if tab is None:
            return
        # sender() 是 EditorWidget，验证其属于当前活动标签页
        editor = self.sender()
        if tab.editor is not editor:
            return
        self._start_preview_debounce()

    def _start_preview_debounce(self) -> None:
        """按当前模式设置防抖间隔并启动定时器。

        - 同步滚动 → 1000ms（减少频繁重渲染）
        - 光标定位 / 无模式 → 300ms（快速响应）
        """
        if self._sync_scrolling_enabled:
            self._preview_timer.setInterval(1000)
        else:
            self._preview_timer.setInterval(300)
        self._preview_timer.start()

    def _update_preview(self) -> None:
        """发起异步 Markdown → HTML 转换（后台线程执行）。"""
        tab = self._active_tab
        if tab is None:
            return
        text = tab.editor_text
        if not text.strip():
            tab.preview.show_placeholder()
            return

        self._preview_request_id += 1
        font_css = self._get_font_face_css(preview_mode=True)
        self._preview_worker.request(text, self._preview_request_id, font_css,
                                      dark_mode=self._dark_mode)

    def _on_preview_ready(self, html: str, request_id: int) -> None:
        """后台转换完成，回主线程更新预览（丢弃过期结果）。

        刷新 HTML 期间临时关闭该标签页的同步滚动，
        避免 setHtml / setValue 触发的 scrollbar valueChanged
        信号回弹到编辑区造成异常滚动。
        """
        if request_id != self._preview_request_id:
            return
        if not html or self._active_tab is None:
            return

        tab = self._active_tab

        # 临时禁止同步滚动，防止 setHtml 触发的 scrollbar 事件干扰编辑区
        tab.set_sync_scrolling(False)

        # ── 光标定位模式：按光标所在行比例跳转预览 ──
        if self._cursor_position_enabled:
            editor = tab.editor
            cursor = editor.textCursor()
            block_number = cursor.blockNumber()
            total_blocks = editor.blockCount()
            cursor_ratio = block_number / max(total_blocks, 1)
            tab.preview.show_preview(html)
            preview_sb = tab.preview.verticalScrollBar()
            preview_sb.setValue(int(cursor_ratio * preview_sb.maximum()))
        else:
            tab.preview.show_preview(html)

        # 恢复同步滚动状态
        tab.set_sync_scrolling(self._sync_scrolling_enabled)

    # ═══════════════════════════════════════════════════════
    #  格式化工具
    # ═══════════════════════════════════════════════════════

    def _insert_format(self, before: str, after: str) -> None:
        """在活动标签页光标位置包裹 Markdown 格式标记。"""
        tab = self._active_tab
        if tab is None:
            return
        editor = tab.editor
        cursor = editor.textCursor()
        selected = cursor.selectedText()

        if selected:
            cursor.insertText(before + selected + after)
        else:
            cursor.insertText(before + after)
            cursor.movePosition(
                cursor.MoveOperation.Left,
                cursor.MoveMode.MoveAnchor,
                len(after),
            )
        editor.setTextCursor(cursor)
        editor.setFocus()

    # ═══════════════════════════════════════════════════════
    #  字体管理
    # ═══════════════════════════════════════════════════════

    def _get_font_face_css(self, preview_mode: bool) -> str:
        """收集所有可用字体的 @font-face CSS。"""
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
        if self._font_manager.active_font:
            entry = RECOMMENDED_FONTS.get(self._font_manager.active_font)
            if entry and self._font_manager.is_usable(entry.key):
                parts.append(
                    f'body {{ font-family: {entry.css_fallback} !important; }}'
                )
        return "\n".join(parts)

    def _setup_font_menu(self, menubar) -> None:
        """初始化顶层「字体」菜单。"""
        font_menu = menubar.addMenu("字体(&F)")
        self._populate_font_menu_actions(font_menu)

    def _populate_font_menu_actions(self, font_menu) -> None:
        """填充字体子菜单项。"""
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
        QSettings().setValue("font", key)
        name = RECOMMENDED_FONTS[key].family_name if key else "系统默认"
        self._update_status(f"字体: {name}")

    def _on_download_font(self, key: str) -> None:
        """在后台线程下载字体，显示进度对话框。"""
        entry = RECOMMENDED_FONTS.get(key)
        if entry is None:
            return

        progress_dlg = QProgressDialog(
            f"正在下载 {entry.family_name} …", "取消", 0, 100, self,
        )
        progress_dlg.setWindowTitle("字体下载")
        progress_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dlg.setMinimumDuration(0)
        progress_dlg.setValue(0)

        thread = QThread(self)
        worker = _FontDownloadWorker(self._font_manager, key)
        worker.moveToThread(thread)

        worker.progress.connect(progress_dlg.setValue)
        worker.finished.connect(
            lambda k: self._on_download_done(k, progress_dlg, thread, worker)
        )
        worker.error.connect(
            lambda k, err: self._on_download_error(k, err, entry,
                                                    progress_dlg, thread, worker)
        )
        progress_dlg.canceled.connect(thread.quit)
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
        """重建字体菜单。"""
        # 菜单栏顺序: 文件(0), 编辑(1), 视图(2), 字体(3)
        font_menu = self.menuBar().actions()[3].menu()
        font_menu.clear()
        self._populate_font_menu_actions(font_menu)

    # ═══════════════════════════════════════════════════════
    #  同步滚动
    # ═══════════════════════════════════════════════════════

    def _on_toggle_sync_scroll(self, enabled: bool) -> None:
        """全局开关：启用/禁用所有标签页的同步滚动。
        与光标定位互斥 —— 开启同步滚动时自动关闭光标定位。
        """
        self._sync_scrolling_enabled = enabled
        if enabled:
            self._cursor_position_enabled = False
            self._cursor_pos_action.setChecked(False)
        for i in range(self._tab_widget.count()):
            tab = self._tab_widget.widget(i)
            if isinstance(tab, Tab):
                tab.set_sync_scrolling(enabled)

    def _on_toggle_cursor_position(self, enabled: bool) -> None:
        """启用/禁用光标定位预览。
        与同步滚动互斥 —— 开启光标定位时自动关闭同步滚动。
        """
        self._cursor_position_enabled = enabled
        if enabled:
            self._sync_scrolling_enabled = False
            self._sync_scroll_action.setChecked(False)
            for i in range(self._tab_widget.count()):
                tab = self._tab_widget.widget(i)
                if isinstance(tab, Tab):
                    tab.set_sync_scrolling(False)

    # ═══════════════════════════════════════════════════════
    #  主题切换
    # ═══════════════════════════════════════════════════════

    def _apply_theme(self, theme_name: str) -> None:
        """切换到指定主题，应用到所有标签页。"""
        theme = THEMES.get(theme_name)
        if theme is None:
            return

        self._current_theme = theme_name
        self._dark_mode = "暗色" in theme_name
        QApplication.instance().setStyleSheet(theme.qss)
        self._engine.theme = theme.engine_theme

        # LaTeX 主题 body max-width 在 QTextBrowser 中可能溢出 → 禁用水平滚动
        latex_mode = theme.engine_theme == "latex"
        scroll_policy = (Qt.ScrollBarPolicy.ScrollBarAlwaysOff if latex_mode
                         else Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        for i in range(self._tab_widget.count()):
            tab = self._tab_widget.widget(i)
            if isinstance(tab, Tab):
                tab.preview.setHorizontalScrollBarPolicy(scroll_policy)

        # 关闭按钮 SVG 图标
        icons_dir = Path(__file__).resolve().parent.parent / "resources" / "icons"
        close_file = "close-dark.svg" if "暗色" in theme_name else "close-light.svg"
        close_icon_path = (icons_dir / close_file).as_posix()
        self._tab_widget.tabBar().setStyleSheet(
            f"QTabBar::close-button {{ image: url({close_icon_path}); }}"
        )

        # 同步所有标签页的行号颜色与光标
        if "暗色" in theme_name:
            bg, fg = "#1e1e1e", "#777"
            self._caret_color = "#d4d4d4"
        else:
            bg, fg = "#f0f0f0", "#999"
            self._caret_color = "#222222"

        self._apply_cursor_settings(bg, fg)

        self._update_preview()

        # 菜单中标记当前主题（仅对有 data() 的主题项；跳过同步滚动等）
        view_menu = self.menuBar().actions()[2]  # 视图菜单
        for action in view_menu.menu().actions():
            if action.data() is not None:
                action.setCheckable(True)
                action.setChecked(action.data() == theme_name)

        # 持久化主题选择
        QSettings().setValue("theme", theme_name)

        self._update_status(f"主题: {theme_name}")

    def _apply_cursor_settings(self, line_bg: str = "", line_fg: str = "") -> None:
        """对所有标签页重新应用行号颜色与光标设置。"""
        for i in range(self._tab_widget.count()):
            tab = self._tab_widget.widget(i)
            if isinstance(tab, Tab):
                self._apply_cursor_settings_to_tab(tab, line_bg, line_fg)

    def _apply_cursor_settings_to_tab(self, tab: "Tab",
                                       line_bg: str = "",
                                       line_fg: str = "") -> None:
        """对单个标签页应用行号颜色与光标设置。"""
        if line_bg:
            tab.editor.set_line_number_colors(line_bg, line_fg)
        tab.editor.setCursorWidth(2)
        tab.editor.set_caret_color(self._caret_color)

    # ═══════════════════════════════════════════════════════
    #  辅助方法
    # ═══════════════════════════════════════════════════════

    def _update_window_title(self) -> None:
        """更新窗口标题显示活动标签页文件名。"""
        tab = self._active_tab
        if tab is None:
            self.setWindowTitle(self.WINDOW_TITLE)
            return
        title = f"{tab.filename} - {self.WINDOW_TITLE}"
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

    # ═══════════════════════════════════════════════════════
    #  设置持久化
    # ═══════════════════════════════════════════════════════

    def _restore_settings(self) -> None:
        """从 QSettings 恢复：主题、字体、窗口几何。
        始终重新应用光标设置（viewport palette 在 show() 时会被 Qt 重建）。
        """
        settings = QSettings()
        # 恢复主题
        saved_theme = settings.value("theme", DEFAULT_THEME)
        if saved_theme != DEFAULT_THEME and saved_theme in THEMES:
            self._apply_theme(saved_theme)
        # 恢复字体
        saved_font = settings.value("font", None)
        if saved_font is not None:
            try:
                self._font_manager.active_font = saved_font
            except ValueError:
                pass
        # 恢复窗口几何
        geometry = settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        # 始终重新应用光标设置，因为 window.show() 后 viewport 被重建
        self._apply_cursor_settings()

    def _save_settings(self) -> None:
        """保存当前设置到 QSettings。"""
        settings = QSettings()
        settings.setValue("theme", self._current_theme)
        settings.setValue("font", self._font_manager.active_font)
        settings.setValue("geometry", self.saveGeometry())

    # ═══════════════════════════════════════════════════════
    #  首次启动
    # ═══════════════════════════════════════════════════════

    def _check_first_launch(self) -> None:
        """首次启动时弹出默认编辑器询问对话框，并注册文件关联。"""
        from ..core.platform_integration import (
            register_as_handler, is_default_handler, set_as_default_handler,
        )

        # 始终注册为「打开方式」选项（幂等）
        register_as_handler()

        settings = QSettings()
        if settings.value("FirstLaunch/Seen", False, type=bool):
            return  # 非首次启动

        settings.setValue("FirstLaunch/Seen", True)

        if is_default_handler():
            return  # 已是默认程序，无需询问

        self._show_default_app_dialog()

    def _show_default_app_dialog(self) -> None:
        """弹出「是否设为默认编辑器？」对话框。"""
        from ..core.platform_integration import set_as_default_handler

        reply = QMessageBox.question(
            self,
            "设为默认编辑器",
            "是否将 MarkdownEditor 设为 .md 文件的默认打开程序？\n\n"
            "您可以稍后在系统设置中更改此选项。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok = set_as_default_handler()
            if not ok:
                QMessageBox.information(
                    self, "提示",
                    "无法自动设置为默认程序。\n"
                    "请右键点击 .md 文件 →「打开方式」→ 选择 MarkdownEditor。",
                )

    # ═══════════════════════════════════════════════════════
    #  自动保存
    # ═══════════════════════════════════════════════════════

    def _autosave_tick(self) -> None:
        """每 60 秒检查所有标签页，满足条件则静默保存。"""
        for i in range(self._tab_widget.count()):
            tab = self._tab_widget.widget(i)
            if not isinstance(tab, Tab):
                continue
            if not tab.should_auto_save():
                continue
            try:
                tab.file_manager.save_file(tab.editor_text, tab.current_path)
                tab.mark_saved()
                idx = self._tab_widget.indexOf(tab)
                if idx >= 0:
                    self._update_tab_title(idx, tab)
                # 状态栏短暂提示
                self._update_status(f"自动保存: {tab.filename}")
            except (IOError, ValueError):
                pass  # 静默忽略，不打断用户

    # ═══════════════════════════════════════════════════════
    #  启动时文件处理
    # ═══════════════════════════════════════════════════════

    def _process_pending_files(self) -> None:
        """处理命令行传入的 .md 文件路径。"""
        app = QApplication.instance()
        if app is None:
            return
        pending = getattr(app, "pending_paths", [])
        for path in pending:
            self._on_drop_markdown_file(path)

        # 连接运行中收到文件的信号
        manager = getattr(app, "_single_instance_manager", None)
        if manager is not None and hasattr(manager, "file_received"):
            manager.file_received.connect(self._on_drop_markdown_file)

        # 连接 macOS QFileOpenEvent 信号
        if hasattr(app, "file_open_requested"):
            app.file_open_requested.connect(self._on_drop_markdown_file)

    # ═══════════════════════════════════════════════════════
    #  窗口关闭
    # ═══════════════════════════════════════════════════════

    def closeEvent(self, event) -> None:
        """关闭窗口前检查所有标签页未保存内容，并停止后台线程。"""
        for i in range(self._tab_widget.count()):
            tab = self._tab_widget.widget(i)
            if isinstance(tab, Tab):
                if not self._maybe_save_tab(tab):
                    event.ignore()
                    return
        self._save_settings()
        self._autosave_timer.stop()
        event.accept()
        self._preview_thread.quit()
        self._preview_thread.wait()
