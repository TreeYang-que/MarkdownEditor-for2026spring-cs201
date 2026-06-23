"""
MarkdownEditor 应用入口。

用法:
    python main.py
"""

import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保 src 包可导入
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main() -> None:
    from src.app import MarkdownApp
    exit_code = MarkdownApp.launch()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
