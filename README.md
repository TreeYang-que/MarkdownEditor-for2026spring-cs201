# MarkdownEditor

基于 PyQt6 的 Markdown 桌面编辑器 —— 2026 春季 CS201 课程项目

## 功能特性

- ✍️ **Markdown 源码编辑** — 带行号的代码编辑器，跨平台字体 fallback
- 👁️ **分屏实时预览** — 左侧编辑，右侧即时渲染（异步后台线程，编辑不卡顿）
- 🎨 **语法高亮** — 代码块自动着色（Pygments CSS 缓存优化）
- 🧮 **LaTeX 数学公式** — `$...$` 行内公式 / `$$...$$` 块级公式，导出 HTML 后 MathJax 自动渲染
- 📂 **文件管理** — 新建、打开、保存，支持拖放/粘贴图片自动插入引用
- 📤 **导出功能** — 导出为自包含 HTML（含 MathJax CDN）
- 🎭 **多主题切换** — 4 套主题：亮色 / 暗色 / LaTeX 亮色 / LaTeX 暗色
  - 默认主题：现代简洁风格
  - LaTeX 学术主题：衬线字体 + 三线表 + 黄金行距（1.618em），适合论文写作
- 🛠️ **格式化工具栏** — 粗体、斜体、标题、列表、链接、公式等，支持键盘快捷键
- ⌨️ **快捷键** — 常用 Markdown 格式一键插入

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
├── src/
│   ├── app.py               # 应用初始化配置
│   ├── ui/                  # 界面组件
│   │   ├── main_window.py   # 主窗口（菜单、布局、主题切换、异步预览线程）
│   │   ├── editor_widget.py # 源码编辑器（行号、字体 fallback、拖放粘贴）
│   │   ├── preview_widget.py# 预览面板（QTextBrowser 实时渲染）
│   │   └── toolbar.py       # 格式化工具栏（公式、代码、列表等）
│   ├── core/                # 核心逻辑
│   │   ├── markdown_engine.py # Markdown→HTML 引擎（含 default/latex 双主题）
│   │   └── file_manager.py  # 文件管理（打开/保存/导出 HTML）
│   ├── themes/              # 主题样式
│   │   └── style.py         # 4 套 QSS 主题 + engine_theme 联动
│   └── resources/           # 图标等静态资源
│       └── icons/
└── tests/                   # 单元测试（24 项）
    └── test_markdown_engine.py
```


## 技术栈

- **GUI**: PyQt6
- **Markdown 解析**: Python-Markdown + PyMdown Extensions
- **代码高亮**: Pygments
- **数学公式**: MathJax 3 (CDN)
- **测试**: pytest

## 致谢

本项目的 LaTeX 学术主题适配自 [Keldos-Li/typora-latex-theme](https://github.com/Keldos-Li/typora-latex-theme)（MIT License），
为 Typora 设计的 LaTeX 风格排版主题。我们将其 SCSS 源码编译并适配到 PyQt6 的 QTextBrowser / 导出 HTML 双渲染管线中：

- **预览模式**：CSS 变量已解析为确定值，兼容 QTextBrowser 有限的 CSS 支持
- **导出模式**：保留完整 CSS 变量，浏览器打开后全特性生效

原始主题版权归 [Keldos-Li](https://github.com/Keldos-Li) 及所有贡献者所有。特此致谢。
