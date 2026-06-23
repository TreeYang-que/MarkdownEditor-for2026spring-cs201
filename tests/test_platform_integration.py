"""
平台集成单元测试。

使用 mock 隔离系统调用，不实际修改注册表 / LaunchServices。
"""

import sys
import os
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch, call

# 确保项目根目录在 path 中
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# ═══════════════════════════════════════════════════════════════
#  辅助函数测试
# ═══════════════════════════════════════════════════════════════

def test_get_app_exe_path_frozen():
    """打包后应返回 sys.executable 的绝对路径。"""
    with patch.dict("sys.modules", {}):
        from src.core import platform_integration
        with patch.object(platform_integration.sys, "frozen", True, create=True):
            with patch.object(platform_integration.sys, "executable",
                              "/path/to/MarkdownEditor.exe"):
                result = platform_integration._get_app_exe_path()
                assert result == os.path.abspath("/path/to/MarkdownEditor.exe")


def test_get_app_exe_path_dev():
    """开发模式应返回 sys.executable 的绝对路径。"""
    with patch.dict("sys.modules", {}):
        from src.core import platform_integration
        with patch.object(platform_integration.sys, "frozen", False, create=True):
            exe = sys.executable
            result = platform_integration._get_app_exe_path()
            assert result == os.path.abspath(exe)


def test_is_bundled_frozen():
    """frozen=True 时 _is_bundled 返回 True。"""
    from src.core import platform_integration
    with patch.object(platform_integration.sys, "frozen", True, create=True):
        assert platform_integration._is_bundled() is True


def test_is_bundled_dev():
    """frozen=False 时 _is_bundled 返回 False。"""
    from src.core import platform_integration
    with patch.object(platform_integration.sys, "frozen", False, create=True):
        assert platform_integration._is_bundled() is False


# ═══════════════════════════════════════════════════════════════
#  Windows 测试（仅在 win32 上运行）
# ═══════════════════════════════════════════════════════════════

if sys.platform == "win32":
    import winreg

    def test_register_as_handler_windows():
        """验证注册表写入路径正确。"""
        from src.core import platform_integration
        with (
            patch.object(platform_integration, "_get_app_exe_path",
                         return_value="C:\\app\\MarkdownEditor.exe"),
            patch.object(platform_integration.winreg, "CreateKey") as mock_create,
            patch.object(platform_integration.winreg, "SetValueEx") as mock_set,
        ):
            mock_create.return_value = MagicMock()
            platform_integration.register_as_handler()

            # 验证至少调用了 CreateKey（ProgID 和 command）
            assert mock_create.call_count >= 2

    def test_set_as_default_handler_windows():
        """验证 .md 默认值设置为 ProgID。"""
        from src.core import platform_integration
        with patch.object(platform_integration, "_get_app_exe_path",
                          return_value="C:\\app\\MarkdownEditor.exe"):
            with patch.object(platform_integration.winreg, "CreateKey") as mock_create:
                with patch.object(platform_integration.winreg, "SetValueEx") as mock_set:
                    with patch.object(platform_integration.ctypes, "windll"):
                        mock_create.return_value = MagicMock()
                        platform_integration.set_as_default_handler()
                        # SetValueEx 至少被调用一次（设置 .md 默认值）
                        assert mock_set.call_count >= 1

    def test_is_registered_true_windows():
        """已注册时应返回 True。"""
        from src.core import platform_integration
        with patch.object(platform_integration.winreg, "OpenKey") as mock_open:
            with patch.object(platform_integration.winreg, "EnumValue") as mock_enum:
                mock_open.return_value = MagicMock()
                mock_enum.side_effect = [
                    ("SomeApp.md", "", 1),
                    ("MarkdownEditor.md", "", 1),
                ]
                assert platform_integration.is_registered() is True

    def test_is_registered_false_windows():
        """未注册时应返回 False。"""
        from src.core import platform_integration
        with patch.object(platform_integration.winreg, "OpenKey") as mock_open:
            mock_open.side_effect = OSError("Key not found")
            assert platform_integration.is_registered() is False

    def test_is_default_handler_true_windows():
        """已是默认时应返回 True。"""
        from src.core import platform_integration
        with patch.object(platform_integration.winreg, "OpenKey") as mock_open:
            with patch.object(platform_integration.winreg, "QueryValueEx") as mock_query:
                mock_open.return_value = MagicMock()
                mock_query.return_value = ("MarkdownEditor.md", 1)
                assert platform_integration.is_default_handler() is True

    def test_is_default_handler_false_windows():
        """非默认时应返回 False。"""
        from src.core import platform_integration
        with patch.object(platform_integration.winreg, "OpenKey") as mock_open:
            with patch.object(platform_integration.winreg, "QueryValueEx") as mock_query:
                mock_open.return_value = MagicMock()
                mock_query.return_value = ("Typora.md", 1)
                assert platform_integration.is_default_handler() is False


# ═══════════════════════════════════════════════════════════════
#  macOS 测试（仅在 darwin 上运行）
# ═══════════════════════════════════════════════════════════════

if sys.platform == "darwin":
    import subprocess

    def test_register_as_handler_dev_macos():
        """开发模式（非 bundled）应返回 False。"""
        from src.core import platform_integration
        with patch.object(platform_integration, "_is_bundled", return_value=False):
            assert platform_integration.register_as_handler() is False

    def test_register_as_handler_bundled_macos():
        """打包后应调用 lsregister。"""
        from src.core import platform_integration
        with patch.object(platform_integration, "_is_bundled", return_value=True):
            with patch.object(platform_integration, "_get_bundle_path",
                              return_value="/Applications/MarkdownEditor.app"):
                with patch.object(platform_integration, "os") as mock_os:
                    mock_os.path.exists.return_value = True
                    with patch.object(platform_integration.subprocess, "run") as mock_run:
                        platform_integration.register_as_handler()
                        mock_run.assert_called_once()

    def test_set_as_default_handler_macos_fallback():
        """osascript 不可用时 duti 应作为降级方案。"""
        from src.core import platform_integration
        with patch.object(platform_integration.subprocess, "run") as mock_run:
            # osascript 失败
            mock_run.side_effect = FileNotFoundError
            result = platform_integration.set_as_default_handler()
            assert result is False


# ═══════════════════════════════════════════════════════════════
#  不依赖平台的通用测试
# ═══════════════════════════════════════════════════════════════

def test_constants():
    """验证常量定义。"""
    from src.core.platform_integration import (
        PROG_ID, APP_NAME, BUNDLE_ID, MARKDOWN_UTI, SUPPORTED_EXTENSIONS,
    )
    assert PROG_ID == "MarkdownEditor.md"
    assert APP_NAME == "MarkdownEditor"
    assert BUNDLE_ID == "com.cs201.markdowneditor"
    assert ".md" in SUPPORTED_EXTENSIONS
    assert ".markdown" in SUPPORTED_EXTENSIONS


if __name__ == "__main__":
    # 简单的手动测试运行器
    tests = [
        test_get_app_exe_path_frozen,
        test_get_app_exe_path_dev,
        test_is_bundled_frozen,
        test_is_bundled_dev,
        test_constants,
    ]
    if sys.platform == "win32":
        tests += [
            test_register_as_handler_windows,
            test_set_as_default_handler_windows,
            test_is_registered_true_windows,
            test_is_registered_false_windows,
            test_is_default_handler_true_windows,
            test_is_default_handler_false_windows,
        ]
    if sys.platform == "darwin":
        tests += [
            test_register_as_handler_dev_macos,
            test_register_as_handler_bundled_macos,
            test_set_as_default_handler_macos_fallback,
        ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            print(f"  PASS  {test_fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {test_fn.__name__} - {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {test_fn.__name__} - {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Result: {passed} passed, {failed} failed ({passed + failed} total)")
    sys.exit(0 if failed == 0 else 1)
