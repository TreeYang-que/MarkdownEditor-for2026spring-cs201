# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件。

用法:
    pyinstaller MarkdownEditor.spec

Windows: 生成 dist/MarkdownEditor/MarkdownEditor.exe（one-folder）
macOS:   生成 dist/MarkdownEditor.app（macOS bundle）
         Bundle 包含 CFBundleDocumentTypes，使应用出现在 .md 文件的「打开方式」菜单中。
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # PyInstaller 提供的 spec 文件所在目录

# ── 入口脚本 ──────────────────────────────────────
ENTRY = str(ROOT / "main.py")
ICON = str(ROOT / "src" / "resources" / "icons" / "256.ico")
APP_NAME = "MarkdownEditor"

# ── 依赖隐式导入 ─────────────────────────────────
hiddenimports = [
    "pygments.lexers",
    "pygments.styles",
    "pymdownx",
    "pymdownx.arithmatex",
    "markdown.extensions",
]

# ── 数据文件 ──────────────────────────────────────
datas = [
    (str(ROOT / "src" / "resources" / "icons"), "src/resources/icons"),
    (str(ROOT / "src" / "resources" / "fonts"), "src/resources/fonts"),
]

a = Analysis(
    [ENTRY],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# ── 可执行文件 ────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON if sys.platform == "win32" else None,
)

# ── macOS Bundle ──────────────────────────────────
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name=f"{APP_NAME}.app",
        icon=ICON,
        bundle_identifier="com.cs201.markdowneditor",
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleIdentifier": "com.cs201.markdowneditor",
            "CFBundleVersion": "1.0.0",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeName": "Markdown Document",
                    "CFBundleTypeRole": "Editor",
                    "LSHandlerRank": "Owner",
                    "LSItemContentTypes": [
                        "net.daringfireball.markdown",
                    ],
                    "CFBundleTypeExtensions": [
                        "md",
                        "markdown",
                        "mdown",
                        "mkd",
                    ],
                },
            ],
            "UTExportedTypeDeclarations": [
                {
                    "UTTypeIdentifier": "net.daringfireball.markdown",
                    "UTTypeTagSpecification": {
                        "public.filename-extension": [
                            "md",
                            "markdown",
                            "mdown",
                            "mkd",
                        ],
                        "public.mime-type": "text/markdown",
                    },
                },
            ],
            "LSMinimumSystemVersion": "10.15",
        },
    )
