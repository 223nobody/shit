# S.H.*.T Space Mirror

一个用于镜像和展示 S.H.*.T Space 学术社区内容的平台，支持文章、新闻、问答等多种内容类型的爬取和展示。

## 项目简介

S.H.*.T (Sciences · Humanities · Information · Technology) Space 是一个学术与文化讨论社区。本项目通过爬虫技术获取社区公开内容，提供以下功能：

- **文章镜像** - 从发酵区获取文章，生成高清页图预览和 PDF 下载
- **新闻聚合** - 展示社区最新公告和动态
- **问答浏览** - 查看培养皿板块的问答内容
- **首页展示** - 社论、最新研究、新闻动态的综合展示

## 技术栈

### 后端
- **Python 3.11+**
- **FastAPI** - Web 框架
- **SQLite** - 数据存储
- **Requests** - HTTP 爬虫
- **PyMuPDF (fitz)** - PDF 处理和渲染

### 前端
- **React 18**
- **React Router** - 路由管理
- **Lucide React** - 图标库
- **原生 CSS** - 样式系统

## 项目结构

```
shit/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI 主应用
│   │   ├── db.py           # 数据库操作
│   │   ├── crawler.py      # 文章爬虫
│   │   ├── content_crawler.py  # 内容爬虫(news/questions)
│   │   └── home_crawler.py     # 首页数据爬虫
│   ├── data/               # 数据目录
│   │   ├── media/
│   │   │   └── pdfs/      # PDF 文件存储
│   │   └── shitspace.db   # SQLite 数据库
│   ├── main.py            # 启动入口
│   └── requirements.txt   # Python 依赖
│
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── App.jsx        # 主应用组件
│   │   ├── App.css        # 全局样式
│   │   ├── pages/         # 页面组件
│   │   │   ├── HomePage.jsx       # 首页
│   │   │   ├── FermentationPage.jsx  # 发酵区文章
│   │   │   └── ContentPage.jsx       # 新闻/问答
│   │   └── components/    # 可复用组件
│   │       ├── ContentCard.jsx
│   │       └── ContentModal.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

## 快速开始

### 环境要求
- Python 3.11 或更高版本
- Node.js 18 或更高版本
- npm 或 yarn

### 后端启动

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

后端服务将在 `http://localhost:8000` 启动，启动后会自动：
1. 初始化数据库（如不存在）
2. 后台线程开始爬取文章、新闻、问答数据

### 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端开发服务器将在 `http://localhost:5173` 启动。

## API 接口

### 文章相关
- `GET /api/articles` - 获取文章列表（支持分页、筛选）
- `GET /api/articles/{id}` - 获取文章详情
- `GET /api/articles/{id}/pages/{page}.png` - 获取文章页图
- `GET /api/articles/{id}/download` - 下载 PDF
- `POST /api/sync` - 手动触发文章同步

### 内容相关
- `GET /api/content/news` - 获取新闻列表
- `GET /api/content/questions` - 获取问答列表
- `GET /api/content/{type}/{id}` - 获取内容详情

### 首页相关
- `GET /api/homepage` - 获取首页数据

### 统计相关
- `GET /api/stats` - 获取系统统计信息
- `GET /api/content/stats` - 获取内容统计

## 页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 首页 | 社论、最新研究、新闻动态 |
| `/fermentation` | 发酵区 | 文章列表，支持筛选和搜索 |
| `/content/news` | 新闻 | 社区公告和动态 |
| `/content/questions` | 培养皿 | 问答内容 |

## 数据爬取

### 自动爬取
服务启动时会自动在后台执行以下爬取任务：
- 文章（最近 5 天）
- 新闻（最近 7 天）
- 问答（最近 7 天）
- 首页数据

### 手动同步
文章页面提供"立即同步"按钮，可手动触发文章爬取。

## 配置说明

### 后端配置
在 `backend/app/crawler.py` 和 `content_crawler.py` 中可调整：
- `DEFAULT_CRAWL_WINDOW_DAYS` - 默认爬取时间窗口（天）
- `DEFAULT_TIMEOUT` - HTTP 请求超时时间（秒）
- `DEFAULT_RENDER_SCALE` - PDF 渲染分辨率

### 前端配置
在 `frontend/vite.config.js` 中配置代理：
```javascript
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

## 数据库结构

### 核心表
- **articles** - 文章信息
- **article_comments** - 文章评论
- **contents** - 新闻/问答内容
- **content_comments** - 内容评论
- **homepage_data** - 首页缓存数据

## 开发说明

### 添加新的内容源

1. 在 `content_crawler.py` 中添加新的 `CONTENT_TYPES` 映射
2. 实现对应的数据获取函数
3. 在 `main.py` 中添加 API 路由
4. 在前端添加对应页面

### 样式系统

项目使用 CSS 变量系统，主要变量定义在 `App.css` 开头：
```css
:root {
  --color-bg-primary: #faf8f3;
  --color-bg-secondary: #f5f0e6;
  --color-text-primary: #1a1612;
  --color-accent: #d4a853;
  /* ... */
}
```

## 注意事项

1. **数据来源** - 本项目仅爬取公开 API 数据，遵守源站使用条款
2. **数据时效性** - 爬取的数据有延迟，非实时同步
3. **PDF 生成** - 首次访问文章页图时会实时渲染，可能需要等待
4. **存储空间** - PDF 文件会占用磁盘空间，定期清理过期文件

## 许可证

本项目仅供学习和研究使用。

## 致谢

- 数据源：[S.H.*.T Space](https://shitspace.xyz/)
- 图标：[Lucide](https://lucide.dev/)
