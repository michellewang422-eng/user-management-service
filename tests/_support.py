"""测试共用的数据库配置：一个内存 SQLite + 依赖覆盖，所有测试文件共享。

为什么要抽出来共享（而不是每个测试文件各写一遍）：
`app.dependency_overrides` 是一个**全局字典**。如果每个测试文件各建一个 engine、
各覆盖一次 get_db，那么后 import 的文件会盖掉先 import 的——跑
`python -m unittest discover` 时，一部分测试的请求会打到「没有建过表」的那个
engine 上，报 `no such table: users`。把 engine 和覆盖逻辑收敛到这一个模块，
所有测试文件共用同一个 engine，就没有这个问题。

三个关键机制（和单文件版一样）：
1. 内存 SQLite（"sqlite://"）：不落盘、跑完即焚，不碰开发用的 users.db
2. StaticPool + check_same_thread=False：让 TestClient 的多个线程共用同一个
   内存连接，否则每个线程各开一个内存库，数据对不上
3. app.dependency_overrides[get_db]：把路由里的 Depends(get_db) 换成连测试库的
   版本，路由代码一行不用改
"""

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
# 必须导入 User，Base 才知道有 users 这张表，下面 create_all 才建得出来
from app.models import User  # noqa: F401


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """和 app/database.py 里的 get_db 结构一样，只是绑到测试用的 engine。"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


class DBTestCase(unittest.TestCase):
    """一个"已经把建表/删表/建 client 这些准备工作写好了的 TestCase"。
    所有用到数据库的测试类都继承它，就不用每个文件再抄一遍 setUp/tearDown。

    这个名字是自己起的（DB + TestCase），不是 unittest 自带的。

    继承链（知识点：`class 子类(父类):` 表示子类自动拥有父类的所有方法）：
      unittest.TestCase   —— 框架提供，带 assertEqual、测试发现机制等
        └─ DBTestCase     —— 我们这里加上"建表/删表/建 client"
             └─ UserAPITestCase / AuthLoginTestCase  —— 各写各的 test_ 方法

    setUp/tearDown 在每个 test_ 方法前后各自动跑一次，保证用例之间互不影响：
    每个用例开始前有一套干净的空表，结束后全部删掉。
    """

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)

    def tearDown(self):
        Base.metadata.drop_all(bind=engine)
