# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py

# 运行测试（不依赖 pytest）
python tests/test_markdown_engine.py

# 用 pytest 运行测试（需安装 pytest）
pytest tests/ -v
```

## Architecture

```
main.py  →  src/app.py  →  src/ui/main_window.py
                │                    │
                │  MarkdownApp       │  owns: MarkdownEngine, FileManager,
                │  (QApplication)    │        EditorWidget, PreviewWidget, MarkdownToolbar
                │                    │
                └─ Fusion style      └─ QSplitter [editor | preview]
```

**Data flow:** `EditorWidget.textChanged` → 300ms debounce timer → `MarkdownEngine.convert()` + `wrap_html()` → `PreviewWidget.setHtml()`

### Key modules

| Module | Role |
|---|---|
| `src/core/markdown_engine.py` | `MarkdownEngine` — wraps Python-Markdown with extensions (fenced_code, tables, codehilite, footnotes, toc, nl2br). `wrap_html()` embeds the converted body into a full HTML document with inline Pygments CSS and preview styling. |
| `src/core/file_manager.py` | `FileManager` — tracks `_current_path` and `_modified` flag. All I/O uses `pathlib.Path`. Throws `IOError` on failure (caught by MainWindow to show QMessageBox). `export_pdf()` is a stub (raises `NotImplementedError`). |
| `src/ui/main_window.py` | `MainWindow` — assembles everything. `_maybe_save()` guards unsaved changes before close/new/open. Theme switching via `QApplication.setStyleSheet()`. Menu actions are hard-coded (no .ui files). View menu at index 2 in the menubar action list. |
| `src/ui/editor_widget.py` | `EditorWidget` — `QPlainTextEdit` with a custom `_LineNumberArea` widget drawn via `QPainter`. `_find_available_font()` probes the system for the best available monospace font from a priority list. Tab inserts 4 spaces; selection indent also works. |
| `src/ui/preview_widget.py` | `PreviewWidget` — `QTextBrowser` (not QWebEngineView, to avoid Chromium dependency). |
| `src/ui/toolbar.py` | `MarkdownToolbar` — emits `format_requested(before, after)` signal. Button definitions are a class-level list; `None` entries become separators. |
| `src/themes/style.py` | Two `Theme` dataclasses (light/dark) in a `THEMES` dict. Each has a `qss` string (Qt stylesheet) and `preview_css` string (injected into preview HTML). Default is "亮色". |

### Key design details

- **No QWebEngineView** — preview uses `QTextBrowser` which only supports a subset of HTML/CSS (no JS, limited CSS). Keep preview CSS simple.
- **Debounce** — text changes don't trigger preview immediately; a 300ms `QTimer` resets on each keystroke. This prevents excessive re-rendering.
- **Font fallback** — `editor_widget.py` has a module-level `_find_available_font()` that iterates a priority list and validates each font with `QFontInfo` before using it. The same pattern should be used for any new font-dependent components.
- **Tests** — `test_markdown_engine.py` has both pytest-style classes and a standalone `run_tests()` function. The engine tests check HTML output strings, not rendered appearance. The markdown library auto-adds `id` attributes to headings (e.g., `<h1 id="_1">`), so heading tests use partial string matching.
- **Theme CSS in `markdown_engine.py`** — the `wrap_html()` method contains a large inline CSS block that is independent of the QSS themes. Dark mode for the preview uses `body.dark` class selectors, but the current implementation always wraps the body in a plain `<body>` tag — the `.dark` class is never actually toggled on the HTML body at runtime. Theme switching only affects QSS (Qt widgets), not the preview CSS.
