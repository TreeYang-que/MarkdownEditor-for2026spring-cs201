"""
平台集成模块 —— 文件关联注册（Windows 注册表 / macOS LaunchServices）。

提供统一 API，内部按 sys.platform 分支到对应实现。
所有操作仅修改用户级配置（HKCU / ~/Library/Preferences），无需管理员权限。
"""

import os
import subprocess
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
#  常量
# ═══════════════════════════════════════════════════════════════

PROG_ID = "MarkdownEditor.md"
APP_NAME = "MarkdownEditor"
APP_DESCRIPTION = "MarkdownEditor — PyQt6 Markdown 桌面编辑器"
BUNDLE_ID = "com.cs201.markdowneditor"
SUPPORTED_EXTENSIONS = (".md", ".markdown", ".mdown", ".mkd")
MARKDOWN_UTI = "net.daringfireball.markdown"


# ═══════════════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════════════

def _get_app_exe_path() -> str:
    """返回当前应用可执行文件的绝对路径。

    PyInstaller 打包后：sys.executable 指向 MarkdownEditor.exe。
    开发模式：sys.executable 指向 python.exe，此时返回 python 路径。
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller / py2app 打包
        return os.path.abspath(sys.executable)
    # 开发模式
    return os.path.abspath(sys.executable)


def _is_bundled() -> bool:
    """检测当前是否以打包的 .app / .exe 运行。"""
    return getattr(sys, 'frozen', False)


# ═══════════════════════════════════════════════════════════════
#  Windows 实现
# ═══════════════════════════════════════════════════════════════

if sys.platform == "win32":
    import ctypes
    import winreg

    def register_as_handler() -> bool:
        """在 HKCU 下注册 MarkdownEditor.md ProgID 并关联 .md 扩展名。"""
        try:
            exe_path = _get_app_exe_path()

            # 1. 创建 ProgID 键
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                  f"Software\\Classes\\{PROG_ID}") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, APP_DESCRIPTION)

            # 2. 创建 shell\open\command
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                f"Software\\Classes\\{PROG_ID}\\shell\\open\\command"
            ) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ,
                                  f'"{exe_path}" "%1"')

            # 3. 添加到 .md 的 OpenWithProgids
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                  "Software\\Classes\\.md\\OpenWithProgids") as key:
                winreg.SetValueEx(key, PROG_ID, 0, winreg.REG_SZ, "")

            # 也注册 .markdown 等扩展名
            for ext in (".markdown", ".mdown", ".mkd"):
                try:
                    with winreg.CreateKey(
                        winreg.HKEY_CURRENT_USER,
                        f"Software\\Classes\\{ext}\\OpenWithProgids"
                    ) as key:
                        winreg.SetValueEx(key, PROG_ID, 0, winreg.REG_SZ, "")
                except OSError:
                    pass

            return True
        except OSError:
            return False

    def set_as_default_handler() -> bool:
        """将 MarkdownEditor.md 设为 .md 文件的默认打开程序。"""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                  "Software\\Classes\\.md") as key:
                # 保存旧值以便可能的恢复
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, PROG_ID)

            # 通知 Shell 刷新文件关联
            try:
                ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
            except Exception:
                pass  # SHChangeNotify 失败不影响主逻辑

            return True
        except OSError:
            return False

    def is_registered() -> bool:
        """检查 MarkdownEditor.md 是否已注册为 .md 的处理程序。"""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                "Software\\Classes\\.md\\OpenWithProgids"
            ) as key:
                idx = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, idx)
                        if name == PROG_ID:
                            return True
                        idx += 1
                    except OSError:
                        break
            return False
        except OSError:
            return False

    def is_default_handler() -> bool:
        """检查 MarkdownEditor.md 是否是 .md 的默认打开程序。"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                "Software\\Classes\\.md") as key:
                default, _ = winreg.QueryValueEx(key, "")
                return default == PROG_ID
        except OSError:
            return False

    def unregister_handler() -> bool:
        """移除 MarkdownEditor.md 的注册信息。"""
        try:
            # 从 OpenWithProgids 中移除
            for ext in SUPPORTED_EXTENSIONS:
                try:
                    with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        f"Software\\Classes\\{ext}\\OpenWithProgids",
                        0, winreg.KEY_SET_VALUE,
                    ) as key:
                        winreg.DeleteValue(key, PROG_ID)
                except OSError:
                    pass

            # 删除 ProgID 键
            try:
                winreg.DeleteKey(
                    winreg.HKEY_CURRENT_USER,
                    f"Software\\Classes\\{PROG_ID}\\shell\\open\\command"
                )
            except OSError:
                pass
            try:
                winreg.DeleteKey(
                    winreg.HKEY_CURRENT_USER,
                    f"Software\\Classes\\{PROG_ID}\\shell\\open"
                )
            except OSError:
                pass
            try:
                winreg.DeleteKey(
                    winreg.HKEY_CURRENT_USER,
                    f"Software\\Classes\\{PROG_ID}\\shell"
                )
            except OSError:
                pass
            try:
                winreg.DeleteKey(
                    winreg.HKEY_CURRENT_USER,
                    f"Software\\Classes\\{PROG_ID}"
                )
            except OSError:
                pass

            return True
        except OSError:
            return False


# ═══════════════════════════════════════════════════════════════
#  macOS 实现
# ═══════════════════════════════════════════════════════════════

elif sys.platform == "darwin":

    def _get_bundle_path() -> str | None:
        """返回当前 .app bundle 路径（仅打包后有效）。"""
        if not _is_bundled():
            return None
        exe = sys.executable
        # PyInstaller 打包后 exe 在 Contents/MacOS/<name>
        if ".app/Contents/MacOS/" in exe:
            return exe.split(".app/Contents/MacOS/")[0] + ".app"
        # py2app 打包类似
        return None

    def register_as_handler() -> bool:
        """强制 LaunchServices 重新索引 .app bundle 的文档类型。
        需要 Info.plist 中已配置 CFBundleDocumentTypes。
        """
        bundle_path = _get_bundle_path()
        if bundle_path is None:
            return False  # 开发模式无法注册

        # lsregister 的可能路径
        lsregister_paths = [
            "/System/Library/Frameworks/CoreServices.framework"
            "/Frameworks/LaunchServices.framework/Support/lsregister",
        ]

        for lsr in lsregister_paths:
            if os.path.exists(lsr):
                try:
                    subprocess.run(
                        [lsr, "-f", bundle_path],
                        capture_output=True, timeout=30,
                    )
                    return True
                except (subprocess.TimeoutExpired, OSError):
                    pass
        return False

    def set_as_default_handler() -> bool:
        """尝试将 MarkdownEditor 设为 .md 的默认打开程序。
        使用 osascript 通过 System Events 更改。
        """
        # 方法1：尝试 osascript
        apple_script = (
            'tell application "System Events"\n'
            '    try\n'
            f'        set default application of (info for (POSIX file "/tmp/test.md"))'
            f' to (path to application id "{BUNDLE_ID}")\n'
            '    end try\n'
            'end tell'
        )
        try:
            result = subprocess.run(
                ["/usr/bin/osascript", "-e", apple_script],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            pass

        # 方法2：尝试通过 LaunchServices 设置 UTI handler
        # 使用 duti（如果已安装）
        try:
            result = subprocess.run(
                ["duti", "-s", BUNDLE_ID, MARKDOWN_UTI, "all"],
                capture_output=True, timeout=10,
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            pass

        return False

    def is_registered() -> bool:
        """检查应用是否已向 LaunchServices 注册了 markdown UTI。"""
        bundle_path = _get_bundle_path()
        if bundle_path is None:
            return False

        # 用 lsregister -dump 检查
        lsregister_paths = [
            "/System/Library/Frameworks/CoreServices.framework"
            "/Frameworks/LaunchServices.framework/Support/lsregister",
        ]
        for lsr in lsregister_paths:
            if not os.path.exists(lsr):
                continue
            try:
                result = subprocess.run(
                    [lsr, "-dump"],
                    capture_output=True, text=True, timeout=30,
                )
                if MARKDOWN_UTI in result.stdout and BUNDLE_ID in result.stdout:
                    return True
            except (subprocess.TimeoutExpired, OSError):
                pass
        return False

    def is_default_handler() -> bool:
        """检查 MarkdownEditor 是否是 .md 的默认打开程序。"""
        # 使用 duti 查询（如果已安装）
        try:
            result = subprocess.run(
                ["duti", "-x", "md"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and BUNDLE_ID in result.stdout:
                return True
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            pass

        # 使用 osascript 查询
        apple_script = (
            'tell application "System Events"\n'
            '    try\n'
            '        set defaultApp to default application of'
            f' (info for (POSIX file "/tmp/test.md"))\n'
            '        return name of defaultApp\n'
            '    on error\n'
            '        return ""\n'
            '    end try\n'
            'end tell'
        )
        try:
            result = subprocess.run(
                ["/usr/bin/osascript", "-e", apple_script],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                app_name = result.stdout.strip()
                return APP_NAME.lower() in app_name.lower()
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            pass

        return False

    def unregister_handler() -> bool:
        """macOS 上移除注册主要通过从 Info.plist 移除 CFBundleDocumentTypes，
        运行时无干净的方式，直接返回 False 引导用户手动操作。
        """
        return False


# ═══════════════════════════════════════════════════════════════
#  Linux / 其他平台 （stub）
# ═══════════════════════════════════════════════════════════════

else:

    def register_as_handler() -> bool:
        return False

    def set_as_default_handler() -> bool:
        return False

    def is_registered() -> bool:
        return False

    def is_default_handler() -> bool:
        return False

    def unregister_handler() -> bool:
        return False
