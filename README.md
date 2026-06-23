# MarkdownEditor

基于 PyQt6 的 Markdown 桌面编辑器 —— 2026 春季 CS201 课程项目

## 功能特性

- ✍️ **Markdown 源码编辑** — 带行号的代码编辑器
- 👁️ **分屏实时预览** — 左侧编辑，右侧即时渲染
- 🎨 **语法高亮** — 代码块自动着色（基于 Pygments）
- 📂 **文件管理** — 新建、打开、保存 Markdown 文件
- 📤 **导出功能** — 导出为 HTML 文件
- 🌗 **主题切换** — 亮色 / 暗色主题
- 🛠️ **工具栏** — 一键插入粗体、斜体、标题、列表、链接等

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
│   │   ├── main_window.py   # 主窗口
│   │   ├── editor_widget.py # 源码编辑器
│   │   ├── preview_widget.py# 预览面板
│   │   └── toolbar.py       # 格式化工具栏
│   ├── core/                # 核心逻辑
│   │   ├── markdown_engine.py # Markdown→HTML 引擎
│   │   └── file_manager.py  # 文件管理
│   ├── themes/              # 主题样式
│   │   └── style.py
│   └── resources/           # 图标等静态资源
│       └── icons/
└── tests/                   # 单元测试
    └── test_markdown_engine.py
```


## 技术栈

- **GUI**: PyQt6
- **Markdown 解析**: Python-Markdown + PyMdown Extensions
- **代码高亮**: Pygments
- **测试**: pytest
