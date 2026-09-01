"""
用 Python 内置的 unittest 框架，测 POST / GET / PUT / DELETE 四类用户接口。

核心思路（3 个知识点）：
1. 不碰真实的 users.db —— 每个测试都用一个「内存里的 SQLite」，跑完即焚，
   互不影响，也不会污染开发用的数据库。
2. 依赖覆盖（dependency override）—— app 里路由函数是靠 Depends(get_db) 拿数据库
   会话的。测试时用 app.dependency_overrides 把 get_db 换成「连测试库」的版本，
   路由代码一行都不用改。
3. TestClient —— FastAPI 提供的「假客户端」，能像发真 HTTP 请求一样调用 app，
   但不用真的起服务器、不用真的联网，速度快、好断言。
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


# ---------------------------------------------------------------------------
# 测试用数据库：内存 SQLite
# ---------------------------------------------------------------------------
# "sqlite://"（后面没有文件路径）表示「建在内存里」，进程结束就没了。
# StaticPool + check_same_thread=False：让 TestClient 的多个线程共用同一个
# 内存连接，否则每个线程各开一个内存库，数据对不上。
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """和 app/database.py 里的 get_db 一模一样，只是绑到测试用的 engine。"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# 关键一步：告诉 app「凡是要用 get_db 的地方，改用 override_get_db」
app.dependency_overrides[get_db] = override_get_db


# 一份合法的创建用户数据，测试里反复用
VALID_PAYLOAD = {
    "email": "alice@example.com",
    "first_name": "Alice",
    "last_name": "Anderson",
}


class UserAPITestCase(unittest.TestCase):
    def setUp(self):
        """每个 test_ 方法跑之前都会执行：建一套干净的空表 + 一个新 client。"""
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)

    def tearDown(self):
        """每个 test_ 方法跑完执行：把所有表删掉，下一个测试从零开始。"""
        Base.metadata.drop_all(bind=engine)

    # 小工具：先塞一个用户进去，返回它的 JSON（很多测试都要先有一条数据）
    def _create_user(self, **overrides):
        payload = {**VALID_PAYLOAD, **overrides}
        resp = self.client.post("/users", json=payload)
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()

    # ------------------------------------------------------------------
    # POST /users
    # ------------------------------------------------------------------
    def test_post_create_user_success(self):
        resp = self.client.post("/users", json=VALID_PAYLOAD)

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        # 前端传的字段应原样返回
        self.assertEqual(body["email"], VALID_PAYLOAD["email"])
        self.assertEqual(body["first_name"], "Alice")
        self.assertEqual(body["last_name"], "Anderson")
        # 数据库自动生成的字段应该有值
        self.assertIsInstance(body["id"], int)
        self.assertIn("created_at", body)
        self.assertIn("updated_at", body)

    def test_post_duplicate_email_returns_400(self):
        self._create_user()
        # 再用同一个 email 创建一次
        resp = self.client.post("/users", json=VALID_PAYLOAD)

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "邮箱已注册")

    def test_post_invalid_email_returns_422(self):
        resp = self.client.post(
            "/users",
            json={**VALID_PAYLOAD, "email": "not-an-email"},
        )
        # Pydantic 的 EmailStr 校验不过 —— FastAPI 自动回 422，路由函数根本没跑
        self.assertEqual(resp.status_code, 422)

    def test_post_missing_field_returns_422(self):
        resp = self.client.post("/users", json={"email": "bob@example.com"})
        self.assertEqual(resp.status_code, 422)

    # ------------------------------------------------------------------
    # GET /users/{user_id}  和  GET /users
    # ------------------------------------------------------------------
    def test_get_user_by_id_success(self):
        created = self._create_user()

        resp = self.client.get(f"/users/{created['id']}")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], created["id"])
        self.assertEqual(resp.json()["email"], "alice@example.com")

    def test_get_user_by_id_not_found_returns_404(self):
        resp = self.client.get("/users/999999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "用户不存在")

    def test_get_user_by_id_non_integer_returns_422(self):
        # URL 里 id 位置传了非数字，: int 转换失败 -> 422
        resp = self.client.get("/users/abc")
        self.assertEqual(resp.status_code, 422)

    def test_get_users_empty_list(self):
        resp = self.client.get("/users")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_get_users_returns_all(self):
        self._create_user(email="a@example.com")
        self._create_user(email="b@example.com")

        resp = self.client.get("/users")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_get_users_filter_by_email_match(self):
        self._create_user(email="a@example.com")
        self._create_user(email="b@example.com")

        resp = self.client.get("/users", params={"email": "b@example.com"})

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["email"], "b@example.com")

    def test_get_users_filter_by_email_no_match_returns_empty_list(self):
        self._create_user(email="a@example.com")

        resp = self.client.get("/users", params={"email": "nobody@example.com"})

        # 筛选列表接口：没匹配到也是 200 + []，不是 404
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    # ------------------------------------------------------------------
    # PUT /users/{user_id}
    # ------------------------------------------------------------------
    def test_put_update_name_success(self):
        created = self._create_user()

        resp = self.client.put(
            f"/users/{created['id']}",
            json={
                "email": created["email"],  # email 不变
                "first_name": "Alicia",
                "last_name": "Anderson",
            },
        )

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["first_name"], "Alicia")
        self.assertEqual(body["id"], created["id"])
        # created_at 不该变
        self.assertEqual(body["created_at"], created["created_at"])

    def test_put_change_email_success(self):
        created = self._create_user()

        resp = self.client.put(
            f"/users/{created['id']}",
            json={
                "email": "alice-new@example.com",
                "first_name": "Alice",
                "last_name": "Anderson",
            },
        )

        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["email"], "alice-new@example.com")

        # 用新 email 能查到，旧 email 查不到
        self.assertEqual(
            len(self.client.get("/users", params={"email": "alice-new@example.com"}).json()),
            1,
        )
        self.assertEqual(
            self.client.get("/users", params={"email": "alice@example.com"}).json(),
            [],
        )

    def test_put_not_found_returns_404(self):
        resp = self.client.put("/users/999999", json=VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "用户不存在")

    def test_put_email_taken_by_other_user_returns_400(self):
        user_a = self._create_user(email="a@example.com")
        self._create_user(email="b@example.com")

        # 想把 A 的 email 改成 B 已经在用的
        resp = self.client.put(
            f"/users/{user_a['id']}",
            json={
                "email": "b@example.com",
                "first_name": "Alice",
                "last_name": "Anderson",
            },
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "邮箱已被其他用户占用")

    def test_put_same_email_same_user_is_allowed(self):
        # 只改姓名、email 传的还是自己当前的 —— 不该被误判成「邮箱被占用」
        created = self._create_user()

        resp = self.client.put(
            f"/users/{created['id']}",
            json={
                "email": created["email"],
                "first_name": "Changed",
                "last_name": "Anderson",
            },
        )

        self.assertEqual(resp.status_code, 200, resp.text)

    def test_put_updated_at_changes(self):
        created = self._create_user()

        resp = self.client.put(
            f"/users/{created['id']}",
            json={
                "email": created["email"],
                "first_name": "Changed",
                "last_name": "Anderson",
            },
        )

        self.assertEqual(resp.status_code, 200, resp.text)
        # models.py 里 updated_at 配了 onupdate=func.now()，PUT 后应该 >= 原值
        self.assertGreaterEqual(resp.json()["updated_at"], created["updated_at"])

    # ------------------------------------------------------------------
    # DELETE /users/{user_id}
    # ------------------------------------------------------------------
    def test_delete_success_returns_204(self):
        created = self._create_user()

        resp = self.client.delete(f"/users/{created['id']}")

        # 204 = 成功且无响应体
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.content, b"")

        # 删完再查，应该 404
        self.assertEqual(
            self.client.get(f"/users/{created['id']}").status_code, 404
        )

    def test_delete_not_found_returns_404(self):
        resp = self.client.delete("/users/999999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "用户不存在")

    def test_delete_twice_second_time_404(self):
        created = self._create_user()

        first = self.client.delete(f"/users/{created['id']}")
        second = self.client.delete(f"/users/{created['id']}")

        self.assertEqual(first.status_code, 204)
        self.assertEqual(second.status_code, 404)


if __name__ == "__main__":
    unittest.main()
