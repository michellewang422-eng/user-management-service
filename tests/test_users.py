"""
用 Python 内置的 unittest 框架，测 POST / GET / PUT / DELETE 四类用户接口。

测试环境（内存 SQLite + 依赖覆盖 + TestClient）统一放在 tests/_support.py 里，
这里直接继承 DBTestCase（它已经写好了 setUp/tearDown：每个用例前建空表、后删表）。

为什么要抽到共用模块、而不是每个测试文件各写一遍：
app.dependency_overrides 是个全局字典，key 是 get_db。如果 test_users.py 和
test_auth.py 各建一个 engine、各覆盖一次，后 import 的会盖掉先 import 的——
跑 `python -m unittest discover` 时，一部分测试的请求会打到「没建过表」的那个
engine 上，报 `no such table: users`。共用一个 engine 就没这个问题。
"""

from tests._support import DBTestCase


# 一份合法的创建用户数据，测试里反复用
VALID_PAYLOAD = {
    "email": "alice@example.com",
    "first_name": "Alice",
    "last_name": "Anderson",
}


class UserAPITestCase(DBTestCase):
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
    import unittest

    unittest.main()
