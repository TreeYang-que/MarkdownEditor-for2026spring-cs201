# MarkdownEditor

基于 PyQt6 的 Markdown 桌面编辑器 —— 2026 春季 CS201 课程项目

## 功能特性

- ✍️ **Markdown 源码编辑** — 带行号的代码编辑器，跨平台字体 fallback，14pt 等宽字体
- 📑 **多标签页** — 像浏览器一样同时编辑多个文件，Ctrl+T 新建 / Ctrl+W 关闭
- 👁️ **分屏实时预览** — 左侧编辑，右侧即时渲染（异步后台线程，编辑不卡顿）
- 🎨 **语法高亮** — 代码块自动着色（Pygments CSS 缓存优化）
- 🧮 **LaTeX 数学公式** — `$...$` 行内公式 / `$$...$$` 块级公式，导出 HTML 后 MathJax 自动渲染
- 🔤 **开源字体支持** — 内置思源宋体/黑体、霞鹜文楷/等宽 4 款推荐字体，一键下载切换
- 📂 **文件管理** — 新建、打开、保存，支持拖放/粘贴图片自动插入引用，拖入 .md 文件直接打开
- 📤 **导出功能** — 导出为自包含 HTML（含 MathJax CDN，字体 base64 内嵌）
- 🎭 **多主题切换** — 3 套主题：亮色 / 暗色 / LaTeX 学术
  - 默认主题：现代简洁风格，亮色浅米黄色标签栏，暗色深灰标签栏
  - LaTeX 学术主题（亮色）：衬线字体 + 三线表 + 黄金行距（1.618em），适合论文写作
- 🛠️ **格式化工具栏** — 粗体、斜体、标题、列表、链接、公式等，支持键盘快捷键
- ⌨️ **快捷键** — 常用 Markdown 格式一键插入
- 💾 **自动保存** — 每 60 秒检测，编辑量 > 300 字符或距上次保存 > 15 分钟自动保存；关闭窗口时已命名文件自动保存
- 🔗 **系统级文件关联** — 安装后自动注册为 .md 文件「打开方式」选项；首次启动询问是否设为默认编辑器（Windows 注册表 / macOS LaunchServices）
- 🪟 **单实例运行** — 双击多个 .md 文件在同一窗口多标签页打开，不重复启动
- 🔄 **设置持久化** — 主题、字体、窗口大小位置重启后自动恢复
- 🖱️ **视图定位模式** — 同步滚动（编辑↔预览比例同步）/ 光标定位（预览跟随光标位置），互斥切换
- 🏗️ **PyInstaller 打包** — 含 `MarkdownEditor.spec` 配置文件，支持 Windows .exe / macOS .app 构建

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

## 项目结构

```
MarkdownEditor/
├── main.py                  # 应用入口
├── requirements.txt         # Python 依赖
├── README.md
├── CLAUDE.md                # AI 协作文档
├── MarkdownEditor.spec      # PyInstaller 打包配置
├── src/
│   ├── app.py               # 应用初始化（QFileOpenEvent / 单实例入口）
│   ├── ui/                  # 界面组件
│   │   ├── main_window.py   # 主窗口（多标签页、菜单、主题/字体、自动保存、预览模式）
│   │   ├── tab.py           # 标签页封装（FileManager + Editor + Preview + 同步滚动）
│   │   ├── editor_widget.py # 源码编辑器（行号、光标、字体 fallback、拖放粘贴）
│   │   ├── preview_widget.py# 预览面板（QTextBrowser 实时渲染）
│   │   └── toolbar.py       # 格式化工具栏（公式、代码、列表等）
│   ├── core/                # 核心逻辑
│   │   ├── markdown_engine.py  # Markdown→HTML 引擎（default/latex 双主题 + 暗色适配）
│   │   ├── file_manager.py     # 文件管理（打开/保存/导出 HTML）
│   │   ├── font_manager.py     # 字体管理（COS 下载、本地注册、CSS 生成）
│   │   ├── platform_integration.py  # 文件关联注册（Windows 注册表 / macOS LaunchServices）
│   │   └── single_instance.py      # 单实例检测 + 文件路径 IPC 转发
│   ├── themes/              # 主题样式
│   │   └── style.py         # 3 套 QSS 主题（亮色 / 暗色 / LaTeX 亮色）
│   └── resources/           # 静态资源
│       ├── icons/           # 应用图标 + SVG 关闭按钮
│       └── fonts/           # 下载的字体文件
└── tests/                   # 单元测试（43 项）
    ├── test_markdown_engine.py
    ├── test_platform_integration.py
    └── test_single_instance.py
```


## 技术栈

- **GUI**: PyQt6 (QTabWidget 多标签页 + Fusion 风格)
- **Markdown 解析**: Python-Markdown + PyMdown Extensions
- **代码高亮**: Pygments
- **数学公式**: MathJax 3 (CDN)
- **字体**: 腾讯云 COS 直链下载，QFontDatabase 本地注册
- **测试**: pytest

## 致谢

本项目的 LaTeX 学术主题适配自 [Keldos-Li/typora-latex-theme](https://github.com/Keldos-Li/typora-latex-theme)（MIT License），
为 Typora 设计的 LaTeX 风格排版主题。我们将其 SCSS 源码编译并适配到 PyQt6 的 QTextBrowser / 导出 HTML 双渲染管线中：

- **预览模式**：CSS 变量已解析为确定值，兼容 QTextBrowser 有限的 CSS 支持
- **导出模式**：保留完整 CSS 变量，浏览器打开后全特性生效

原始主题版权归 [Keldos-Li](https://github.com/Keldos-Li) 及所有贡献者所有。特此致谢。
