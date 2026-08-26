from fastapi import FastAPI

# Base：总登记处；engine：数据库连接引擎，两者都在database.py里定义好
from app.database import Base, engine
# 必须导入models，Python才会真正"读到"User类的定义，Base才知道要建users这张表
from app import models

# 启动时检查：如果Base登记名单里的表（目前是users）在数据库里还不存在，就建出来
# 已存在的表不会被重复建、不会清空数据
Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello, user-service!"}
