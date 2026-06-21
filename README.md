# 学生社团管理与活动报名系统

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python 3.x + FastAPI + SQLAlchemy ORM |
| 前端 | Vue 3 (Composition API) + Vite + Element Plus + Pinia |
| 数据库 | SQLite（默认）/ MySQL（可选） |
| AI/ML | DeepSeek API、OpenCV Haar Cascade + LBPH 人脸识别、Sentence-Transformers + ChromaDB 语义搜索 |
| 打包 | PyInstaller（生成独立 Windows exe） |

## 目录结构

```
源码/
├── backend/                   # FastAPI 后端
│   ├── main.py                # 入口：FastAPI 应用、SPA 托管、生命周期
│   ├── requirements.txt       # Python 依赖列表
│   ├── .env.template          # 环境变量模板（首次运行会复制为 .env）
│   └── app/
│       ├── api/               # API 路由（activities、auth、clubs、AI服务等）
│       ├── core/              # 配置（.env读取）、安全（密码哈希/JWT）
│       ├── models/            # SQLAlchemy ORM 模型（User、Club、Activity等）
│       ├── schemas/           # Pydantic 请求/响应模型
│       └── services/          # 业务逻辑层（AI聊天、人脸识别、海报生成等）
├── frontend/                  # Vue 3 前端
│   ├── package.json           # npm 依赖
│   ├── vite.config.js         # Vite 构建配置
│   └── src/
│       ├── views/             # 页面组件（登录、仪表盘、社团、活动、签到、AI等）
│       ├── components/        # 通用组件
│       ├── stores/            # Pinia 状态管理
│       ├── router/            # Vue Router 路由
│       ├── api/               # Axios HTTP 客户端
│       └── styles/            # CSS 设计系统（主题、动画、暗色模式）
└── club_system.spec           # PyInstaller 打包配置
```

## 后端运行

```bash
cd backend

# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
# 将 .env.template 复制为 .env，编辑数据库和API密钥等配置
copy .env.template .env

# 3. 启动服务（默认 http://localhost:8000）
python main.py
```

## 前端开发运行

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 启动开发服务器（默认 http://localhost:5173）
npm run dev

# 3. 生产构建（输出到 dist/，由后端托管）
npm run build
```

## 打包为 Windows exe

```bash
# 在项目根目录执行
pyinstaller club_system.spec

# 输出：dist/社团管理系统.exe
# 首次运行时自动生成 .env 模板文件，编辑配置后重新启动即可
```

## 核心功能

- 用户注册/登录（JWT 认证）
- 社团管理（创建、加入、审批、成员管理）
- 活动管理（发布、报名、签到）
- AI 聊天助手（DeepSeek API + RAG 知识库）
- AI 智能推荐与文案生成
- AI 海报自动生成
- 人脸识别签到（OpenCV LBPH）
- 管理员审批面板
- 通知系统
- 暗色主题 / 玻璃态 UI
