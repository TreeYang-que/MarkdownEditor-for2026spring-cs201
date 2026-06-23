"""
字体管理器 —— 推荐字体的检测、下载、注册与 CSS 生成。
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from threading import Thread
from urllib.request import urlretrieve

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  COS 字体存储
# ═══════════════════════════════════════════════════════════════

# 腾讯云 COS 字体直链基地址（所有字体文件存放于此）
FONT_BASE_URL = (
    "https://picture-for-public-1379103641.cos.ap-beijing.myqcloud.com/fonts"
)


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
    files: list[str] = field(default_factory=list)  # COS 上的字体文件名
    description: str = ""                       # 中文描述

    @property
    def download_urls(self) -> list[str]:
        """返回每个字体文件的完整 COS 下载地址。"""
        return [f"{FONT_BASE_URL}/{f}" for f in self.files]


RECOMMENDED_FONTS: dict[str, FontEntry] = {
    "source-han-serif": FontEntry(
        key="source-han-serif",
        family_name="Source Han Serif SC",
        css_fallback='"Source Han Serif SC", "Noto Serif CJK SC", '
                     '"华文宋体", "宋体-简", "SimSun", serif',
        category="serif",
        files=[
            "SourceHanSerifCN-Regular.otf",
            "SourceHanSerifCN-Bold.otf",
        ],
        description="思源宋体 — Adobe/Google 开源宋体，适合正文排版",
    ),
    "source-han-sans": FontEntry(
        key="source-han-sans",
        family_name="Source Han Sans SC",
        css_fallback='"Source Han Sans SC", "Noto Sans CJK SC", '
                     '"微软雅黑", "PingFang SC", sans-serif',
        category="sans-serif",
        files=[
            "SourceHanSansSC-Regular.otf",
            "SourceHanSansSC-Bold.otf",
        ],
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

# 字体文件大小（字节），用于下载进度计算。None 表示首次运行时自动探测。
# pylint: disable=line-too-long
FONT_FILE_SIZES: dict[str, int]
FONT_FILE_SIZES = {
    "SourceHanSerifCN-Regular.otf": 11_626_108,
    "SourceHanSerifCN-Bold.otf": 13_731_606,
    "SourceHanSansSC-Regular.otf": 13_433_469,
    "SourceHanSansSC-Bold.otf": 14_739_026,
    "LXGWWenKai-Regular.ttf": 13_233_580,
    "LXGWWenKaiMono-Regular.ttf": 12_516_388,
}


# ═══════════════════════════════════════════════════════════════
#  下载辅助函数
# ═══════════════════════════════════════════════════════════════

def _dl_single(url: str, dest_path: Path, on_progress: callable) -> None:
    """从 COS 下载单个字体文件（带重试）。"""
    import time

    max_retries = 3
    for attempt in range(max_retries):
        try:
            urlretrieve(url, str(dest_path), on_progress)
            return  # 成功
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (2 ** attempt))  # 1s → 2s → 4s


def _download_font_files(
    entry, dest: Path, on_progress: callable, on_error: callable, key: str
) -> None:
    """从 COS 逐文件下载字体（不再使用 zip 包）。"""
    files = entry.files
    for idx, filename in enumerate(files):
        url = f"{FONT_BASE_URL}/{filename}"
        dest_path = dest / filename

        if dest_path.exists():
            # 文件已存在，跳过下载
            file_progress = FONT_FILE_SIZES.get(filename)
            if file_progress and on_progress:
                on_progress(min(int((idx + 1) / len(files) * 100), 100))
            continue

        # 单个文件下载进度回调（含文件索引，计算总体进度）
        def _file_progress(count, block_size, total, _idx=idx, _n=len(files)):
            if on_progress:
                total_sz = FONT_FILE_SIZES.get(filename)
                if total_sz and total_sz > 0:
                    pct = min(int((_idx * total_sz + count * block_size) /
                                   (_n * total_sz / len(files) * 2) * 100), 99)
                else:
                    if total > 0:
                        pct = min(int((_idx * 100 + count * block_size / total * 100) / _n), 99)
                on_progress(pct)

        _dl_single(url, dest_path, _file_progress)

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
        """后台线程下载字体。自动识别 zip 包或单个 .ttf/.otf 文件。

        Args:
            key: 字体 key。
            on_progress(percent: int): 进度回调。
            on_done(key: str): 下载完成回调。
            on_error(key: str, error: str): 出错回调。
        """
        entry = RECOMMENDED_FONTS.get(key)
        if entry is None:
            if on_error:
                on_error(key, f"未知字体: {key}")
            return

        def _run() -> None:
            try:
                _download_font_files(
                    entry, self._fonts_dir, on_progress, on_error, key
                )
                if on_done:
                    on_done(key)
            except Exception as e:
                logger.exception("下载字体失败: %s", key)
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
