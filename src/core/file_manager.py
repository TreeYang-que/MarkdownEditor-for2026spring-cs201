"""
文件管理器 —— 处理 Markdown 文件的打开、保存和导出。
"""

import os
from pathlib import Path


class FileManager:
    """文件读写与导出管理。"""

    # 支持的文件类型过滤
    MARKDOWN_FILTER = "Markdown 文件 (*.md *.markdown);;所有文件 (*.*)"
    HTML_FILTER = "HTML 文件 (*.html *.htm);;所有文件 (*.*)"
    PDF_FILTER = "PDF 文件 (*.pdf)"

    def __init__(self):
        self._current_path: str | None = None
        self._modified: bool = False

    # ── 属性 ──────────────────────────────────────────

    @property
    def current_path(self) -> str | None:
        """当前打开的文件路径，未保存过则为 None。"""
        return self._current_path

    @property
    def current_dir(self) -> str:
        """当前文件所在目录，未保存过则返回用户主目录。"""
        if self._current_path:
            return str(Path(self._current_path).parent)
        return str(Path.home())

    @property
    def filename(self) -> str:
        """当前文件名（不含路径），未保存过返回"未命名"。 """
        if self._current_path:
            return Path(self._current_path).name
        return "未命名.md"

    @property
    def modified(self) -> bool:
        """文件是否有未保存的修改。"""
        return self._modified

    def mark_modified(self) -> None:
        """标记文件已被修改。"""
        self._modified = True

    # ── 文件操作 ──────────────────────────────────────

    def read_file(self, path: str) -> str:
        """读取 Markdown 文件内容。

        Args:
            path: 文件路径。

        Returns:
            文件文本内容。文件不存在则返回空字符串。
        """
        try:
            content = Path(path).read_text(encoding="utf-8")
            self._current_path = path
            self._modified = False
            return content
        except (FileNotFoundError, PermissionError, OSError) as e:
            raise IOError(f"无法打开文件: {e}") from e

    def save_file(self, content: str, path: str | None = None) -> str:
        """保存内容到文件。

        Args:
            content: 要保存的 Markdown 文本。
            path: 目标路径，为 None 时使用上次的路径。

        Returns:
            实际写入的文件路径。

        Raises:
            IOError: 写入失败时抛出。
        """
        target = path or self._current_path
        if target is None:
            raise ValueError("未指定保存路径")

        try:
            Path(target).write_text(content, encoding="utf-8")
            self._current_path = target
            self._modified = False
            return target
        except (PermissionError, OSError) as e:
            raise IOError(f"保存失败: {e}") from e

    def export_html(self, html_content: str, path: str) -> str:
        """导出为 HTML 文件。

        Args:
            html_content: 完整的 HTML 文档字符串。
            path: 导出路径。

        Returns:
            导出的文件路径。
        """
        try:
            Path(path).write_text(html_content, encoding="utf-8")
            return path
        except (PermissionError, OSError) as e:
            raise IOError(f"导出失败: {e}") from e

    def export_pdf(self, html_content: str, path: str) -> str:
        """导出为 PDF 文件（暂未实现）。

        Args:
            html_content: HTML 内容。
            path: 导出路径。
        """
        raise NotImplementedError("PDF 导出功能尚未实现")

    def new_file(self) -> None:
        """新建文件，重置状态。"""
        self._current_path = None
        self._modified = False
