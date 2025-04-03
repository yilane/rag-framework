# 手工制作一个RAG框架

一个从零开始实现的 RAG (Retrieval Augmented Generation) 系统，不依赖现有的 RAG 框架。该项目旨在提供一个轻量级、可定制的知识库问答解决方案。

![RAG Frontend](images/RAG.png)

## 项目概述

本项目是一个完全自主实现的 RAG 系统，通过将文档分块、向量化存储、相似度检索等核心功能模块化实现，使用户能够构建自己的知识库问答系统。

### 核心特性

- 文档分块：支持自定义大小的文档分块策略
- 向量化存储：将文本块转换为向量并高效存储
- 相似度检索：基于向量相似度进行智能匹配
- 无框架依赖：不依赖 LangChain 等重量级 RAG 框架
- 跨平台支持：同时支持 Windows 和 Ubuntu 环境

## 部署安装

### 拉取代码

你可以通过克隆此仓库到你的本地机器来开始：

```shell
git clone https://github.com/yline007/ragdev-project.git
```

然后导航至目录，并按照部署前端或后端的指示开始操作。

### 部署前端 (Ubuntu) 

#### 1. 检查是否已安装 npm：

- 进入前端项目目录（例如 `cd web-vue3/`）。
- 在终端中运行命令：`npm -v`
- 如果已安装，将显示 npm 的版本号。

#### 2. 安装 Node.js 和 npm：

- 更新 apt 软件包列表：`sudo apt update`
- 安装 Node.js 和 npm：`sudo apt install nodejs npm -y`
- **备注**：项目中使用的`node`版本为`v22.14.0` ， `npm`版本为`10.9.2`

#### 3. 安装前端组件：

- 运行 `npm install` 命令来安装项目依赖的前端组件。

#### 4. 运行前端组件：

修改`web-vue3/src/config/api.js`中的代码环境地址`apiBaseUrl`

```bash
const config = {
  development: {
    baseUrl: 'http://localhost:8001'
  },
  production: {
    baseUrl: 'http://api.example.com'
  },
  test: {
    baseUrl: 'http://localhost:8001'
  }
}
```

运行 `npm run dev` 命令来安装项目依赖的前端组件。

```bash
# 默认是 development 环境
npm run dev

# 或者指定环境
npm run dev --mode production
```

### 部署后端 (Ubuntu) 

本项目使用 Python v3.10 开发，完整 Python 依赖软件包见requirements_ubun.txt 和 requirements_win.txt。

- Windows 环境： [requirements_win.txt](https://github.com/yline007/ragdev-project/blob/main/requirements_win.txt)
- Ubuntu 环境： [requirements_ubun.txt](https://github.com/yline007/ragdev-project/blob/main/requirements_ubun.txt)

关键依赖的官方文档如下：

- Python 环境管理 [Miniconda](https://docs.conda.io/projects/miniconda/en/latest/)

#### 1. 安装 Miniconda

```shell
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm -rf ~/miniconda3/miniconda.sh
```

安装完成后，建议新建一个 Python 虚拟环境，命名为 `rag-project`。

```shell
conda create -n rag-project python=3.11

# 激活环境
conda activate rag-project 
```

#### 2. 安装后端依赖：

```
pip install -r requirements_ubun.txt
```

#### 3. 配置 OpenAI API Key

根据你使用的命令行工具，在 `~/.bashrc` 或 `~/.zshrc` 中配置 `OPENAI_API_KEY` 环境变量：

```shell
export OPENAI_API_KEY="xxxx"
export DEEPSEEK_API_KEY="xxxx"
```

#### 4. 启动后端

上述开发环境安装完成后，使用`uvicorn`启动后端

```shell
# 进入后端代码目录
cd backend/
# 启动
uvicorn main:app --reload --port 8001 --host 0.0.0.0
```

*(请确保您的后端主文件是 `main.py` 并且 FastAPI 应用实例名为 `app`。如果端口 `8001` 被占用，请更换为其他可用端口。)*

这条命令是使用 Uvicorn 运行一个 ASGI (Asynchronous Server Gateway Interface) 应用程序的指令。让我们分解一下它的各个部分：

- **`uvicorn`**: 这是 Uvicorn 的命令行接口。Uvicorn 是一个闪电般快速的 ASGI 服务器，基于 uvloop 和 httptools 构建。它主要用于运行现代 Python Web 框架，如 FastAPI 和 Starlette。

- **`main:app`**: 这部分指定了要运行的 ASGI 应用程序的位置。

  - **`main`**: 这通常指的是一个名为 `main.py` 的 Python 文件（模块）。

  - `app`: 这指的是在 `main.py` 文件中定义的一个名为 `app`的变量。这个变量应该是一个 ASGI 应用程序实例。例如，如果你在使用 FastAPI，你可能会在  `main.py` 中有类似这样的代码：

    ```python
    from fastapi import FastAPI
    
    app = FastAPI()
    
    @app.get("/")
    async def read_root():
        return {"Hello": "World"}
    ```

- **`--reload`**: 这是一个非常有用的开发选项。当使用这个标志时，Uvicorn 会监视你的应用程序代码文件的更改。一旦检测到任何更改，它会自动重新启动服务器。这使得在开发过程中可以快速迭代，而无需手动停止和启动服务器。

- **`--port 8001`**: 这个选项指定了 Uvicorn 服务器应该监听的网络端口。在这里，服务器将被配置为在 `8001` 端口上接收传入的 HTTP 请求。如果不指定端口，Uvicorn 默认会使用 `8000` 端口。

**总而言之，这条命令的作用是：**

启动 Uvicorn ASGI 服务器，加载 `main.py` 文件中名为 `app` 的 ASGI 应用程序。服务器将在 `8001` 端口上监听传入的请求，并且在应用程序代码发生更改时自动重新加载。

这通常是在开发基于 ASGI 框架（如 FastAPI 或 Starlette）构建的 Web 应用程序时启动服务器的标准命令。


## 技术架构

### 技术栈
- 后端：Python FastAPI
- 向量数据库：Milvus、Chroma
- 前端：Vue3 + Vite
- 后端：Python 

## 项目架构 

### 整体项目结构
```
.
├── backend/               # 后端项目目录
├── web-vue3/              # 前端项目目录
├── requirements_ubun.txt  # Ubuntu环境依赖
├── requirements_win.txt   # Windows环境依赖
└── README.md              # 项目说明文档
```

### 后端项目架构 
```
backend/
├── main.py                # 主入口文件
├── services/              # 服务层目录
│   ├── archive/          # 归档服务目录
│   ├── chunking_service.py    # 文本分块服务
│   ├── embedding_service.py   # 文本嵌入服务
│   ├── generation_service.py  # 内容生成服务
│   ├── loading_service.py     # 数据加载服务
│   ├── parsing_service.py     # 文本解析服务
│   ├── search_service.py      # 搜索服务
│   └── vector_store_service.py # 向量存储服务
├── utils/                # 工具目录
├── logs/                # 日志目录
├── temp/                # 临时文件目录
├── 01-loaded-docs/      # 原始文档存储目录
├── 01-chunked-docs/     # 分块后文档存储目录
├── 02-embedded-docs/    # 向量化后文档存储目录
├── 03-vector-store/     # 向量数据库存储目录
├── 04-search-results/   # 搜索结果存储目录
└── 05-generation-results/ # 生成结果存储目录
```

### 前端项目架构 
```
web-vue3/
├── public/            # 静态资源目录
├── src/               # 源代码目录
│   ├── assets/        # 项目资源文件(图片、字体等)
│   ├── components/    # 可复用的Vue组件
│   ├── router/        # 路由配置
│   ├── store/         # 状态管理
│   ├── views/         # 页面级组件
│   ├── App.vue        # 根组件
│   └── main.js        # 应用入口文件
├── index.html         # 项目HTML模板
├── package.json       # 项目依赖和脚本配置
├── vite.config.js     # Vite构建工具配置
├── tailwind.config.js # Tailwind CSS配置
└── postcss.config.js  # PostCSS配置
```

## 常见部署异常

