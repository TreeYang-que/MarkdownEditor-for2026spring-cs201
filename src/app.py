"""
应用初始化配置模块。
"""

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication


class MarkdownApp(QApplication):
    """Markdown 编辑器应用类，封装 QApplication 初始化。"""

    APP_NAME = "MarkdownEditor"
    ORG_NAME = "CS201"

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

    @staticmethod
    def launch() -> int:
        """启动应用程序。

        在 main.py 中调用，返回退出码（传给 sys.exit）。
        """
        app = MarkdownApp(sys.argv)

        # 延迟导入主窗口，避免循环依赖
        from src.ui.main_window import MainWindow

        window = MainWindow()
        window.show()

        return app.exec()
