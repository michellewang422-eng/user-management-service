"""
用 unittest 测简化版登录接口 POST /auth/login。

测试环境（内存 SQLite + 依赖覆盖 + TestClient）和 test_users.py 共用同一份，
放在 tests/_support.py 里，这里直接继承 DBTestCase。

不在这里再建一个 engine 的原因：app.dependency_overrides 是全局字典，两个测试
文件各覆盖一次的话，后 import 的会盖掉先 import 的，跑 discover 时会有一半测试
打到没建表的 engine 上报 `no such table: users`。共用一个 engine 就没这问题。
"""

from tests._support import DBTestCase


class AuthLoginTestCase(DBTestCase):
    def _create_user(self, email="alice@example.com"):
        resp = self.client.post(
            "/users",
            json={"email": email, "first_name": "Alice", "last_name": "A"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()

    # ------------------------------------------------------------------
    # POST /auth/login
    # ------------------------------------------------------------------
    def test_login_with_registered_email_returns_profile(self):
        created = self._create_user(email="alice@example.com")

        resp = self.client.post("/auth/login", json={"email": "alice@example.com"})

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        # 登录成功应返回这个用户的完整 profile
        self.assertEqual(body["id"], created["id"])
        self.assertEqual(body["email"], "alice@example.com")
        self.assertEqual(body["first_name"], "Alice")

    def test_login_with_unregistered_email_returns_401(self):
        # 库里没有这个 email
        resp = self.client.post("/auth/login", json={"email": "nobody@example.com"})

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["detail"], "邮箱未注册")

    def test_login_with_invalid_email_format_returns_422(self):
        # Pydantic 的 EmailStr 校验不过 -> FastAPI 自动回 422，登录函数根本没跑
        resp = self.client.post("/auth/login", json={"email": "not-an-email"})
        self.assertEqual(resp.status_code, 422)

    def test_login_missing_email_field_returns_422(self):
        resp = self.client.post("/auth/login", json={})
        self.assertEqual(resp.status_code, 422)

    def test_login_body_not_a_json_object_returns_422(self):
        # 防御性用例：body 是个裸字符串（合法 JSON，但不是对象），
        # 而不是 {"email": ...}。应被 FastAPI 挡下返回 422，登录函数不执行、不崩。
        # content= 直接发原始 body，绕过 json= 的自动包装
        resp = self.client.post(
            "/auth/login",
            content='"alice@example.com"',
            headers={"content-type": "application/json"},
        )
        self.assertEqual(resp.status_code, 422)

    def test_login_failure_body_has_no_other_user_data(self):
        # 库里有 A，但用一个没注册的 email 登录 —— 401 的响应体应该是一句
        # 通用提示，不该把库里其他用户（A）的姓名/邮箱等信息带出来
        self._create_user(email="alice@example.com")

        resp = self.client.post("/auth/login", json={"email": "bob@example.com"})

        self.assertEqual(resp.status_code, 401)
        self.assertNotIn("alice", resp.text)


if __name__ == "__main__":
    import unittest

    unittest.main()
