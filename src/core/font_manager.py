"""
字体管理器 —— 推荐字体的检测、下载、注册与 CSS 生成。
"""

import logging
import os
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse
from urllib.request import urlretrieve

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  推荐字体注册表
# ═══════════════════════════════════════════════════════════════

@dataclass
class FontEntry:
    """一条推荐字体记录。"""
    key: str                                    # 内部标识
    family_name: str                            # 字体族名（系统注册名 / CSS font-family）
    css_fallback: str                           # CSS font-family 字符串（含回退）
    category: str                               # "serif" / "sans-serif" / "mono"
    download_url: str                           # zip 包下载地址
    files: list[str] = field(default_factory=list)  # zip 中需要提取的字体文件名
    description: str = ""                       # 中文描述


RECOMMENDED_FONTS: dict[str, FontEntry] = {
    "source-han-serif": FontEntry(
        key="source-han-serif",
        family_name="Source Han Serif SC",
        css_fallback='"Source Han Serif SC", "Noto Serif CJK SC", '
                     '"华文宋体", "宋体-简", "SimSun", serif',
        category="serif",
        download_url=(
            "https://github.com/adobe-fonts/source-han-serif/releases/"
            "download/2.003R/14_SourceHanSerifCN.zip"
        ),
        files=[
            "SourceHanSerifCN-Regular.otf",
            "SourceHanSerifCN-Bold.otf",
        ],
        description="思源宋体 — Adobe 开源宋体，7 种字重，适合正文排版",
    ),
}


# ═══════════════════════════════════════════════════════════════
#  FontManager
# ═══════════════════════════════════════════════════════════════

class FontManager:
    """推荐字体检测、下载、注册。"""

    def __init__(self, fonts_dir: Path | str):
        self._fonts_dir = Path(fonts_dir).resolve()
        self._fonts_dir.mkdir(parents=True, exist_ok=True)
        self._active_font: str | None = None  # 用户当前选择的字体 key

    # ── 属性 ──────────────────────────────────────────

    @property
    def active_font(self) -> str | None:
        return self._active_font

    @active_font.setter
    def active_font(self, key: str | None) -> None:
        if key is not None and key not in RECOMMENDED_FONTS:
            raise ValueError(f"未知字体: {key}")
        self._active_font = key

    @property
    def fonts_dir(self) -> Path:
        return self._fonts_dir

    # ── 检测 ──────────────────────────────────────────

    def is_downloaded(self, key: str) -> bool:
        """检查推荐字体是否已下载到本地 fonts 目录。"""
        entry = RECOMMENDED_FONTS.get(key)
        if entry is None:
            return False
        return all(
            (self._fonts_dir / f).exists()
            for f in entry.files
        )

    def is_system_installed(self, family_name: str) -> bool:
        """检查字体是否已安装到操作系统。"""
        try:
            from PyQt6.QtGui import QFontDatabase
        except ImportError:
            return False
        from PyQt6.QtWidgets import QApplication
        if QApplication.instance() is None:
            return False
        families = QFontDatabase.families()
        return family_name in families

    def list_available(self) -> list[dict]:
        """列出所有推荐字体的状态。返回结构:
        [{"key": "...", "name": "...", "downloaded": bool,
          "installed": bool, "description": "..."}, ...]
        """
        result = []
        for key, entry in RECOMMENDED_FONTS.items():
            result.append({
                "key": key,
                "name": entry.family_name,
                "description": entry.description,
                "downloaded": self.is_downloaded(key),
                "installed": self.is_system_installed(entry.family_name),
                "active": self._active_font == key,
            })
        return result

    def is_usable(self, key: str) -> bool:
        """字体是否可用（本地已下载 或 系统已安装）。"""
        entry = RECOMMENDED_FONTS.get(key)
        if entry is None:
            return False
        return self.is_downloaded(key) or self.is_system_installed(
            entry.family_name
        )

    # ── 下载 ──────────────────────────────────────────

    def download_font(
        self,
        key: str,
        on_progress: callable = None,
        on_done: callable = None,
        on_error: callable = None,
    ) -> None:
        """后台线程下载字体 zip，解压提取指定文件。

        Args:
            key: 字体 key。
            on_progress(percent: int): 进度回调（主线程安全需自行处理）。
            on_done(key: str): 下载完成回调。
            on_error(key: str, error: str): 出错回调。
        """
        entry = RECOMMENDED_FONTS.get(key)
        if entry is None:
            if on_error:
                on_error(key, f"未知字体: {key}")
            return

        def _run() -> None:
            zip_path = self._fonts_dir / f"{key}.zip"
            try:
                # 下载
                def _progress(count: int, block_size: int, total: int) -> None:
                    if total > 0 and on_progress:
                        pct = min(int(count * block_size / total * 100), 100)
                        on_progress(pct)

                urlretrieve(entry.download_url, str(zip_path), _progress)

                # 解压指定文件
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for name in entry.files:
                        zf.extract(name, str(self._fonts_dir))

                # 清理 zip
                try:
                    zip_path.unlink()
                except OSError:
                    pass

                if on_done:
                    on_done(key)

            except Exception as e:
                logger.exception("下载字体失败: %s", key)
                try:
                    zip_path.unlink(missing_ok=True)
                except OSError:
                    pass
                if on_error:
                    on_error(key, str(e))

        t = Thread(target=_run, daemon=True)
        t.start()

    # ── 注册 ──────────────────────────────────────────

    def load_local_fonts(self) -> int:
        """将 fonts 目录下的所有字体注册到 Qt（QFontDatabase.addApplicationFont）。

        Returns:
            成功加载的字体文件数。
        """
        try:
            from PyQt6.QtGui import QFontDatabase
        except ImportError:
            return 0

        from PyQt6.QtWidgets import QApplication
        if QApplication.instance() is None:
            return 0

        count = 0
        for ext in (".otf", ".ttf"):
            for path in self._fonts_dir.glob(f"*{ext}"):
                result = QFontDatabase.addApplicationFont(str(path))
                if result >= 0:
                    count += 1
        return count

    # ── CSS 生成 ──────────────────────────────────────

    def get_font_face_css(self, key: str) -> str:
        """为导出 HTML 生成 @font-face CSS（base64 内嵌，自包含）。"""
        entry = RECOMMENDED_FONTS.get(key)
        if entry is None or not self.is_downloaded(key):
            return ""

        import base64
        lines = []
        for filename in entry.files:
            fpath = self._fonts_dir / filename
            if not fpath.exists():
                continue
            data = base64.b64encode(fpath.read_bytes()).decode("ascii")
            # 读字体名推断 weight
            weight = "normal"
            if "Bold" in filename:
                weight = "bold"
            ext = fpath.suffix.lstrip(".").lower()
            fmt_map = {"otf": "opentype", "ttf": "truetype"}
            fmt = fmt_map.get(ext, "truetype")

            lines.append(
                f'@font-face {{\n'
                f'    font-family: "{entry.family_name}";\n'
                f'    src: url(data:font/{fmt};base64,{data}) '
                f'format("{fmt}");\n'
                f'    font-weight: {weight};\n'
                f'}}'
            )
        return "\n".join(lines)

    def get_preview_font_face_css(self, key: str) -> str:
        """为预览面板生成 @font-face CSS（本地文件路径引用）。"""
        entry = RECOMMENDED_FONTS.get(key)
        if entry is None or not self.is_downloaded(key):
            return ""

        lines = []
        for filename in entry.files:
            fpath = self._fonts_dir / filename
            if not fpath.exists():
                continue
            weight = "normal"
            if "Bold" in filename:
                weight = "bold"

            lines.append(
                f'@font-face {{\n'
                f'    font-family: "{entry.family_name}";\n'
                f'    src: url("{fpath.as_posix()}");\n'
                f'    font-weight: {weight};\n'
                f'}}'
            )
        return "\n".join(lines)
