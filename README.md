# User Management Service

一个独立运行的用户管理后端服务，提供基础的用户信息管理API

## 环境搭建（从零开始）

### 1. 安装前置工具

- **Git**：Mac第一次使用git相关命令时，系统通常会自动弹出安装"Command Line Tools"的提示，按提示安装即可
- **Python 3**：Mac不一定自带可用的 `python3`，如果没有，去 [python.org](https://www.python.org/) 下载安装，或用 Homebrew：
  ```bash
  brew install python3
  ```

### 2. 克隆项目

```bash
git clone https://github.com/michellewang422-eng/user-management-service.git
cd user-management-service
```

### 3. 建立并激活虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

激活成功后，终端提示符前面会出现 `(.venv)` 标记。

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 启动服务器

```bash
uvicorn app.main:app --reload
```

看到类似 `Uvicorn running on http://127.0.0.1:8000` 的提示即代表启动成功。

### 6. 验证

浏览器打开：

- `http://127.0.0.1:8000` —— 应显示 `{"message": "Hello, user-service!"}`
- `http://127.0.0.1:8000/docs` —— 应显示自动生成的Swagger UI接口文档