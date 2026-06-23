"""
主题模块 —— 提供亮色/暗色主题的 QSS 样式表。
"""

from dataclasses import dataclass


@dataclass
class Theme:
    """一个主题的 QSS 样式定义。"""
    name: str
    qss: str           # Qt 组件样式
    preview_css: str   # 预览面板 HTML 背景色注入


# ── 亮色主题 ──────────────────────────────────────────

LIGHT_QSS = """
/* ── 全局 ── */
QMainWindow {
    background-color: #f5f5f5;
}

QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
    padding: 2px;
    font-size: 13px;
}

QMenuBar::item:selected {
    background-color: #e8f0fe;
    border-radius: 4px;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 28px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #e8f0fe;
    color: #1a1a1a;
}

QMenu::separator {
    height: 1px;
    background: #e0e0e0;
    margin: 4px 8px;
}

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
    padding: 4px;
    spacing: 4px;
}

QToolButton {
    padding: 6px 12px;
    border: 1px solid transparent;
    border-radius: 4px;
    font-size: 13px;
    color: #333;
}

QToolButton:hover {
    background-color: #e8f0fe;
    border-color: #c0d8f8;
}

QToolButton:pressed {
    background-color: #d0e0f8;
}

QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e0e0e0;
    color: #666;
    font-size: 12px;
    padding: 2px 8px;
}

QSplitter::handle {
    background-color: #e0e0e0;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #4a90d9;
}

QPlainTextEdit {
    background-color: #ffffff;
    border: none;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 14px;
    padding: 8px;
    selection-background-color: #b3d4ff;
}

QTextBrowser {
    background-color: #ffffff;
    border: none;
    font-size: 15px;
}

QScrollBar:vertical {
    background: #f0f0f0;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #c0c0c0;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #999;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #f0f0f0;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #c0c0c0;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""

LIGHT_PREVIEW_CSS = """
body {
    background-color: #ffffff;
    color: #333;
}
"""

# ── 暗色主题 ──────────────────────────────────────────

DARK_QSS = """
QMainWindow {
    background-color: #1e1e1e;
}

QMenuBar {
    background-color: #2d2d2d;
    border-bottom: 1px solid #3e3e3e;
    padding: 2px;
    font-size: 13px;
    color: #ccc;
}

QMenuBar::item:selected {
    background-color: #3e3e3e;
    border-radius: 4px;
}

QMenu {
    background-color: #2d2d2d;
    border: 1px solid #3e3e3e;
    border-radius: 6px;
    padding: 4px;
    color: #ccc;
}

QMenu::item {
    padding: 6px 28px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #094771;
    color: #fff;
}

QMenu::separator {
    height: 1px;
    background: #3e3e3e;
    margin: 4px 8px;
}

QToolBar {
    background-color: #252526;
    border-bottom: 1px solid #3e3e3e;
    padding: 4px;
    spacing: 4px;
}

QToolButton {
    padding: 6px 12px;
    border: 1px solid transparent;
    border-radius: 4px;
    font-size: 13px;
    color: #ccc;
}

QToolButton:hover {
    background-color: #3e3e3e;
    border-color: #555;
}

QToolButton:pressed {
    background-color: #094771;
}

QStatusBar {
    background-color: #2d2d2d;
    border-top: 1px solid #3e3e3e;
    color: #999;
    font-size: 12px;
    padding: 2px 8px;
}

QSplitter::handle {
    background-color: #3e3e3e;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #569cd6;
}

QPlainTextEdit {
    background-color: #1e1e1e;
    border: none;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 14px;
    padding: 8px;
    color: #d4d4d4;
    selection-background-color: #264f78;
}

QTextBrowser {
    background-color: #1e1e1e;
    border: none;
    font-size: 15px;
    color: #ccc;
}

QScrollBar:vertical {
    background: #2d2d2d;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #555;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #777;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #2d2d2d;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #555;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""

DARK_PREVIEW_CSS = """
body {
    background-color: #1e1e1e;
    color: #ccc;
}
body.dark {
    background: #1e1e1e;
    color: #ccc;
}
"""

# ── 主题注册表 ────────────────────────────────────────

THEMES: dict[str, Theme] = {
    "亮色": Theme(name="亮色", qss=LIGHT_QSS, preview_css=LIGHT_PREVIEW_CSS),
    "暗色": Theme(name="暗色", qss=DARK_QSS, preview_css=DARK_PREVIEW_CSS),
}

DEFAULT_THEME = "亮色"
