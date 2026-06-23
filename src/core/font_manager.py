"""
字体管理器 —— 推荐字体的检测、下载、注册与 CSS 生成。
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.request import urlretrieve

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  COS 字体存储
# ═══════════════════════════════════════════════════════════════

FONT_BASE_URL = (
    "https://picture-for-public-1379103641.cos.ap-beijing.myqcloud.com/fonts"
)


# ═══════════════════════════════════════════════════════════════
#  推荐字体注册表
# ═══════════════════════════════════════════════════════════════

@dataclass
class FontEntry:
    key: str
    family_name: str
    css_fallback: str
    category: str                               # "serif" / "sans-serif" / "mono"
    files: list[str] = field(default_factory=list)
    description: str = ""

    @property
    def download_urls(self) -> list[str]:
        return [f"{FONT_BASE_URL}/{f}" for f in self.files]


RECOMMENDED_FONTS: dict[str, FontEntry] = {
    "source-han-serif": FontEntry(
        key="source-han-serif",
        family_name="Source Han Serif SC",
        css_fallback='"Source Han Serif SC", "Noto Serif CJK SC", '
                     '"华文宋体", "宋体-简", "SimSun", serif',
        category="serif",
        files=["SourceHanSerifCN-Regular.otf", "SourceHanSerifCN-Bold.otf"],
        description="思源宋体 — Adobe/Google 开源宋体，适合正文排版",
    ),
    "source-han-sans": FontEntry(
        key="source-han-sans",
        family_name="Source Han Sans SC",
        css_fallback='"Source Han Sans SC", "Noto Sans CJK SC", '
                     '"微软雅黑", "PingFang SC", sans-serif',
        category="sans-serif",
        files=["SourceHanSansSC-Regular.otf", "SourceHanSansSC-Bold.otf"],
        description="思源黑体 — Adobe/Google 开源黑体，适合标题和 UI",
    ),
    "lxgw-wenkai": FontEntry(
        key="lxgw-wenkai",
        family_name="LXGW WenKai",
        css_fallback='"LXGW WenKai", "霞鹜文楷", '
                     '"楷体", "华文楷体", "KaiTi", cursive',
        category="serif",
        files=["LXGWWenKai-Regular.ttf"],
        description="霞鹜文楷 — 开源楷体风格，字形优美，适合正文和引用",
    ),
    "lxgw-wenkai-mono": FontEntry(
        key="lxgw-wenkai-mono",
        family_name="LXGW WenKai Mono",
        css_fallback='"LXGW WenKai Mono", "霞鹜文楷等宽", '
                     '"Consolas", "Courier New", monospace',
        category="mono",
        files=["LXGWWenKaiMono-Regular.ttf"],
        description="霞鹜文楷等宽 — 代码友好的楷体等宽字体",
    ),
}

# 字体文件大小（字节），用于下载进度计算
FONT_FILE_SIZES: dict[str, int] = {
    "SourceHanSerifCN-Regular.otf": 11_626_108,
    "SourceHanSerifCN-Bold.otf":    13_731_606,
    "SourceHanSansSC-Regular.otf":  13_433_469,
    "SourceHanSansSC-Bold.otf":     14_739_026,
    "LXGWWenKai-Regular.ttf":       13_233_580,
    "LXGWWenKaiMono-Regular.ttf":   12_516_388,
}


# ═══════════════════════════════════════════════════════════════
#  下载辅助函数（纯 Python，无 Qt 依赖，在工作线程中调用）
# ═══════════════════════════════════════════════════════════════

def _dl_single(url: str, dest_path: Path, on_progress: callable = None) -> None:
    """从 COS 下载单个字体文件（带 3 次重试 + 指数量退避）。"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            urlretrieve(url, str(dest_path), on_progress)
            return
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (2 ** attempt))


def _download_font_files(
    entry: FontEntry, dest: Path, on_progress: callable = None
) -> None:
    """从 COS 逐文件下载字体文件。"""
    files = entry.files
    n = len(files)
    total_bytes = sum(FONT_FILE_SIZES.get(f, 0) for f in files) or 1
    downloaded_bytes = 0

    for idx, filename in enumerate(files):
        url = f"{FONT_BASE_URL}/{filename}"
        dest_path = dest / filename
        file_size = FONT_FILE_SIZES.get(filename, 0)

        if dest_path.exists():
            downloaded_bytes += file_size
            if on_progress:
                on_progress(min(int(downloaded_bytes / total_bytes * 100), 100))
            continue

        # 带闭包捕获的进度回调（累计字节 → 百分比）
        def _file_progress(
            count: int, block_size: int, _total: int,
            _idx: int = idx, _fs: int = file_size,
        ) -> None:
            nonlocal downloaded_bytes
            cur = min(count * block_size, _fs) if _fs else count * block_size
            pct = min(
                int((downloaded_bytes + cur) / total_bytes * 100), 99
            )
            if on_progress:
                on_progress(pct)

        _dl_single(url, dest_path, _file_progress)
        downloaded_bytes += file_size

    if on_progress:
        on_progress(100)


# ═══════════════════════════════════════════════════════════════
#  FontManager
# ═══════════════════════════════════════════════════════════════

class FontManager:
    """推荐字体检测、下载、注册。"""

    def __init__(self, fonts_dir: Path | str):
        self._fonts_dir = Path(fonts_dir).resolve()
        self._fonts_dir.mkdir(parents=True, exist_ok=True)
        self._active_font: str | None = None

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
        entry = RECOMMENDED_FONTS.get(key)
        if entry is None:
            return False
        return all((self._fonts_dir / f).exists() for f in entry.files)

    def is_system_installed(self, family_name: str) -> bool:
        try:
            from PyQt6.QtGui import QFontDatabase
        except ImportError:
            return False
        from PyQt6.QtWidgets import QApplication
        if QApplication.instance() is None:
            return False
        return family_name in QFontDatabase.families()

    def list_available(self) -> list[dict]:
        return [{
            "key": key,
            "name": e.family_name,
            "description": e.description,
            "downloaded": self.is_downloaded(key),
            "installed": self.is_system_installed(e.family_name),
            "active": self._active_font == key,
        } for key, e in RECOMMENDED_FONTS.items()]

    def is_usable(self, key: str) -> bool:
        entry = RECOMMENDED_FONTS.get(key)
        if entry is None:
            return False
        return self.is_downloaded(key) or self.is_system_installed(entry.family_name)

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


# ═══════════════════════════════════════════════════════════════
#  FontDownloadWorker — QObject 工作线程（安全桥接
#  下载线程与 Qt 主线程）
# ═══════════════════════════════════════════════════════════════

class _FontDownloadWorker(QObject):
    """在 QThread 中执行字体下载，通过信号安全通知主线程。

    使用方式（在 MainWindow 中）:
        thread = QThread()
        worker = _FontDownloadWorker(font_manager, key)
        worker.moveToThread(thread)
        worker.progress.connect(on_progress)   # int
        worker.finished.connect(on_done)       # str
        worker.error.connect(on_error)         # str, str
        thread.started.connect(worker.run)
        thread.start()
    """

    progress = pyqtSignal(int)          # 下载进度 0-100
    finished = pyqtSignal(str)          # 字体 key
    error = pyqtSignal(str, str)        # 字体 key, 错误信息

    def __init__(self, font_manager: FontManager, key: str):
        super().__init__()
        self._fm = font_manager
        self._key = key

    def run(self) -> None:
        """在工作线程中执行（由 QThread.started 信号触发）。"""
        entry = RECOMMENDED_FONTS.get(self._key)
        if entry is None:
            self.error.emit(self._key, f"未知字体: {self._key}")
            return
        try:
            _download_font_files(entry, self._fm.fonts_dir,
                                 on_progress=self.progress.emit)
            self.finished.emit(self._key)
        except Exception as e:
            logger.exception("下载字体失败: %s", self._key)
            self.error.emit(self._key, str(e))
