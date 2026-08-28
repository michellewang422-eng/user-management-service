from fastapi import FastAPI

# Base：总登记处；engine：数据库连接引擎，两者都在database.py里定义好
from app.database import Base, engine
# 必须导入models，Python才会真正"读到"User类的定义，Base才知道要建users这张表
from app import models
# 导入app/routers/users.py里定义好的路由文件
from app.routers import users

# 启动时检查：如果Base登记名单里的表（目前是users）在数据库里还不存在，就建出来
# 已存在的表不会被重复建、不会清空数据
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 把users.py里定义的那个router（里面有POST /users）正式"挂载"到主应用app上
# 之后路由越来越多，只需要不断include_router，不用把所有代码堆在这一个文件里
app.include_router(users.router)


@app.get("/")
def read_root():
    return {"message": "Hello, user-service!"}
