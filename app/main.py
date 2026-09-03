from fastapi import FastAPI
# CORSMiddleware：控制"允许哪些来源的网页调用这个后端"
from fastapi.middleware.cors import CORSMiddleware

# Base：总登记处；engine：数据库连接引擎，两者都在database.py里定义好
from app.database import Base, engine
# 必须导入models，Python才会真正"读到"User类的定义，Base才知道要建users这张表
from app import models
# 导入app/routers/里定义好的路由文件：users（用户增删改查）、auth（登录）
from app.routers import users, auth

# 启动时检查：如果Base登记名单里的表（目前是users）在数据库里还不存在，就建出来
# 已存在的表不会被重复建、不会清空数据
Base.metadata.create_all(bind=engine)

app = FastAPI()

# ---- CORS ----
# 前端页面（user-service-web/ 里的 html）和这个后端不是同一个"源"：
# "源" = 协议 + 域名 + 端口，三者都一样才算同源。
# 前端一般跑在 http://127.0.0.1:5500 之类，后端在 http://127.0.0.1:8000，端口不同 = 不同源。
# 浏览器出于安全，默认禁止网页向"另一个源"的接口发请求（会看到 CORS 报错）。
# 下面明确列出前端页面的地址，告诉浏览器"这些源可以访问我"。
# 端口按你实际打开前端用的改：VS Code Live Server 常见是 5500，python -m http.server 是你指定的那个。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8777",
        "http://127.0.0.1:8777",
    ],
    allow_methods=["*"],   # 允许 GET/POST/PUT/DELETE 等所有方法
    allow_headers=["*"],   # 允许所有请求头（比如 Content-Type）
)

# 把各个router正式"挂载"到主应用app上
# 之后路由越来越多，只需要不断include_router，不用把所有代码堆在这一个文件里
app.include_router(users.router)
# auth.router 自带 prefix="/auth"，所以它里面的 /login 对外就是 POST /auth/login
app.include_router(auth.router)


@app.get("/")
def read_root():
    return {"message": "Hello, user-service!"}
