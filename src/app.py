"""
应用初始化配置模块。
"""

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QEvent, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication


class MarkdownApp(QApplication):
    """Markdown 编辑器应用类，封装 QApplication 初始化。"""

    APP_NAME = "MarkdownEditor"
    ORG_NAME = "CS201"

    # ── 信号 ──────────────────────────────────────────

    file_open_requested = pyqtSignal(str)

    def __init__(self, argv: list[str]):
        super().__init__(argv)

        self.setApplicationName(self.APP_NAME)
        self.setOrganizationName(self.ORG_NAME)

        # 高 DPI 支持
        self.setStyle("Fusion")

        # 应用图标
        icons_dir = Path(__file__).resolve().parent / "resources" / "icons"
        icon_path = icons_dir / "256.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    # ── QFileOpenEvent 处理 ───────────────────────────

    def event(self, event: QEvent) -> bool:
        """拦截 macOS QFileOpenEvent —— 应用运行时用户双击 .md 文件。"""
        if event.type() == QEvent.Type.FileOpen:
            from PyQt6.QtGui import QFileOpenEvent
            file_open = event
            if isinstance(file_open, QFileOpenEvent):
                file_path = file_open.file()
                if file_path:
                    self.file_open_requested.emit(file_path)
                    return True
        return super().event(event)

    # ── 启动入口 ──────────────────────────────────────

    @staticmethod
    def launch() -> int:
        """启动应用程序。

        在 main.py 中调用，返回退出码（传给 sys.exit）。
        """
        from src.core.single_instance import SingleInstanceManager

        # ── 单实例检测 ────────────────────────────
        manager = SingleInstanceManager()
        if not manager.try_acquire():
            # 已有实例在运行 —— 转发文件路径后退出
            paths = _collect_file_paths(sys.argv[1:])
            manager.send_file_paths(paths)
            return 0

        # ── 扫描命令行传入的 .md 文件路径 ──────────
        pending_paths = _collect_file_paths(sys.argv[1:])

        app = MarkdownApp(sys.argv)
        app.pending_paths = pending_paths
        app._single_instance_manager = manager

        # 延迟导入主窗口，避免循环依赖
        from src.ui.main_window import MainWindow

        window = MainWindow()
        window.show()

        return app.exec()


def _collect_file_paths(args: list[str]) -> list[str]:
    """从命令行参数中收集存在的 .md 文件路径（绝对路径）。"""
    paths: list[str] = []
    for arg in args:
        if not arg.startswith("-"):
            p = os.path.abspath(arg)
            if os.path.isfile(p) and p.lower().endswith((".md", ".markdown", ".mdown", ".mkd")):
                paths.append(p)
    return paths
