# MarkdownEditor

基于 PyQt6 的 Markdown 桌面编辑器 —— 2026 春季 CS201 课程项目

==由于组员没有用Mac的，还未确定是否适用于Mac的系统==

## 功能特性

### 编辑体验

- **多标签页编辑** — 同时编辑多个文件，支持 Ctrl+W 关闭标签页，拖入 .md 文件自动在新标签页打开
- **行号显示** — 编辑器左侧显示行号区域，支持亮色/暗色主题自适应配色
- **智能字体选择** — 按优先级自动探测系统可用等宽字体（Cascadia Code → JetBrains Mono → Fira Code → … → monospace），14pt 大小，Tab 键插入 4 空格
- **格式化工具栏** — 提供粗体、斜体、删除线、标题（H1-H3）、列表、链接、图片、代码、引用、分隔线、LaTeX 公式等快捷按钮
- **键盘快捷键** — 常用操作均有快捷键绑定：Ctrl+B（粗体）、Ctrl+I（斜体）、Ctrl+K（链接）、Ctrl+\`（行内代码）、Ctrl+Shift+C（代码块）等

### 实时预览

- **分屏实时渲染** — 左侧编辑，右侧即时预览，基于 QTextBrowser 实现，无需 Chromium 依赖
- **异步后台线程** — Markdown→HTML 转换在独立 QThread 中执行，大文档编辑不卡顿；通过请求 ID 机制自动丢弃过时结果
- **代码语法高亮** — 借助 Pygments 对代码块进行语法着色，暗色模式匹配 monokai 主题，CSS 在引擎初始化时预生成以优化性能
- **LaTeX 数学公式** — 基于 `pymdownx.arithmatex`（generic 模式），支持 `$...$` 行内公式和 `$$...$$` 块级公式；导出 HTML 后由 MathJax 3 CDN 自动渲染
- **视图定位模式** — 支持同步滚动（编辑↔预览比例同步）和光标定位（预览跟随光标位置），两种模式互斥切换，防抖间隔根据模式动态调整

### 主题与排版

- **三套主题** — 亮色（现代简洁）、暗色（深色护眼）、LaTeX 亮色（学术风格，衬线字体 + 三线表 + 黄金行距 1.618em）
- **暗色模式全覆盖** — 不仅 QSS 组件暗色化，预览面板也通过 `body.dark` 选择器完整适配（代码块、引用块、表格、公式高亮全面覆写）
- **LaTeX 学术主题** — 适配自 [Keldos-Li/typora-latex-theme](https://github.com/Keldos-Li/typora-latex-theme)（MIT License），预览模式下 CSS 变量解析为确定值以兼容 QTextBrowser，导出时保留完整 CSS 变量供浏览器全特性渲染

### 字体系统

- **四款推荐开源中文字体** — 思源宋体、思源黑体、霞鹜文楷、霞鹜文楷等宽，从腾讯云 COS 下载
- **一键下载切换** — 字体菜单显示下载/安装状态，后台线程下载并显示进度；已安装到系统的字体可直接使用
- **双模式字体嵌入** — 预览面板使用 `file://` 本地路径加载字体；导出 HTML 时转为 base64 Data URI 内嵌，文件自包含

### 文件与数据管理

- **文件操作** — 新建、打开、保存（标准快捷键 Ctrl+N / Ctrl+O / Ctrl+S）、另存为（Ctrl+Shift+S）
- **拖放与粘贴图片** — 拖入或粘贴图片文件自动插入 `![name](path)` 引用语法，相对路径自动解析
- **拖入 Markdown 文件** — 拖入单个 .md 文件在新标签页中打开
- **导出 HTML** — 导出为自包含 HTML 文件（MathJax CDN + Pygments CSS + 字体 base64 内嵌），始终使用亮色 CSS
- **自动保存** — 每 60 秒检测，满足条件（编辑量 > 300 次变更或距上次保存 > 15 分钟）自动保存已命名文件；关闭窗口时静默保存已命名文件，未命名文件弹窗提示

### 系统集成

- **文件关联注册** — 安装后自动注册为 .md 文件打开方式；首次启动询问是否设为默认编辑器（Windows 注册表 / macOS LaunchServices）
- **单实例运行** — 基于 QLocalServer/QLocalSocket，双击多个 .md 文件在同一窗口多标签页打开，不重复启动进程
- **设置持久化** — 主题、字体、窗口大小和位置通过 QSettings 自动保存，重启后恢复
- **PyInstaller 打包** — 提供 `MarkdownEditor.spec` 配置文件，支持构建 Windows .exe / macOS .app

## 环境配置

### 1. 克隆仓库

```bash
git clone https://github.com/TreeYang-que/MarkdownEditor-for2026spring-cs201.git
cd MarkdownEditor-for2026spring-cs201
```

### 2. 创建虚拟环境

```bash
python -m venv venv
```

**激活虚拟环境：**

- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 运行测试

```bash
# 不依赖 pytest
python tests/test_markdown_engine.py

# 使用 pytest（需安装）
pytest tests/ -v

# 运行单个测试
pytest tests/test_markdown_engine.py::TestMarkdownEngine::test_bold -v
```

## 项目结构

```
MarkdownEditor/
├── main.py                     # 应用入口
├── requirements.txt            # Python 依赖
├── README.md
├── CLAUDE.md                   # AI 协作文档
├── MarkdownEditor.spec         # PyInstaller 打包配置
├── src/
│   ├── app.py                  # 应用初始化（QFileOpenEvent / 单实例入口）
│   ├── ui/                     # 界面组件
│   │   ├── main_window.py      # 主窗口（多标签页、菜单、主题/字体、自动保存、预览模式）
│   │   ├── tab.py              # 标签页封装（FileManager + Editor + Preview + 同步滚动）
│   │   ├── editor_widget.py    # 源码编辑器（行号、光标、字体 fallback、拖放粘贴）
│   │   ├── preview_widget.py   # 预览面板（QTextBrowser 实时渲染）
│   │   └── toolbar.py          # 格式化工具栏（公式、代码、列表等）
│   ├── core/                   # 核心逻辑
│   │   ├── markdown_engine.py  # Markdown→HTML 引擎（default/latex 双主题 + 暗色适配）
│   │   ├── file_manager.py     # 文件管理（打开/保存/导出 HTML）
│   │   ├── font_manager.py     # 字体管理（COS 下载、本地注册、CSS 生成）
│   │   ├── platform_integration.py  # 文件关联注册（Windows 注册表 / macOS LaunchServices）
│   │   └── single_instance.py      # 单实例检测 + 文件路径 IPC 转发
│   ├── themes/                 # 主题样式
│   │   └── style.py            # 3 套 QSS 主题（亮色 / 暗色 / LaTeX 亮色）
│   └── resources/              # 静态资源
│       ├── icons/              # 应用图标 + 关闭按钮 SVG
│       └── fonts/              # 下载的字体文件
└── tests/                      # 单元测试（46 项）
    ├── test_markdown_engine.py
    ├── test_platform_integration.py
    └── test_single_instance.py
```

## 技术栈

| 技术 | 用途 |
|---|---|
| PyQt6 | GUI 框架（QTabWidget 多标签页 + Fusion 风格） |
| Python-Markdown + PyMdown Extensions | Markdown 解析（fenced_code, tables, codehilite, footnotes, toc, nl2br, sane_lists, arithmatex） |
| Pygments | 代码块语法高亮（亮色默认 + 暗色 monokai） |
| MathJax 3 (CDN) | LaTeX 数学公式渲染 |
| 腾讯云 COS | 推荐字体托管与分发 |
| QFontDatabase | 应用级字体注册 |
| QLocalServer / QLocalSocket | 单实例进程间通信 |
| QSettings | 用户设置持久化 |
| pytest | 单元测试框架 |

## 致谢

本项目的 LaTeX 学术主题适配自 [Keldos-Li/typora-latex-theme](https://github.com/Keldos-Li/typora-latex-theme)（MIT License），原始主题版权归 [Keldos-Li](https://github.com/Keldos-Li) 及所有贡献者所有。

我们将原始 SCSS 源码编译并适配到 PyQt6 QTextBrowser / 导出 HTML 双渲染管线：

- **预览模式**：CSS 变量已解析为确定值，兼容 QTextBrowser 有限的 CSS 子集
- **导出模式**：保留完整 CSS 变量，浏览器环境全特性生效

## 许可证

本项目采用 [MIT License](LICENSE)。

```
MIT License

Copyright (c) 2026 TreeYang-que
```

本项目使用的第三方组件遵循其各自的许可证：
- **PyQt6** — GPL v3 / Commercial
- **Python-Markdown** — BSD License
- **PyMdown Extensions** — MIT License
- **Pygments** — BSD License
- **[typora-latex-theme](https://github.com/Keldos-Li/typora-latex-theme)** — MIT License
