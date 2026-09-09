"""CORS 中间件的行为（PR-13 给前端放行时在 app/main.py 加的）。

CORS 只对"浏览器里的网页 JS"生效：浏览器发跨源请求会带上 Origin 头，并检查
响应里有没有对应的 Access-Control-Allow-Origin。这里用 TestClient 手动带上
Origin 头来验证中间件配置对了。用 GET / 这个不碰数据库的路由，跟其它测试文件
互不影响。
"""

import unittest

from fastapi.testclient import TestClient

from app.main import app


class CORSTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_allowed_origin_gets_cors_header(self):
        # allow_origins 列表里的源 → 响应带上 Access-Control-Allow-Origin
        resp = self.client.get("/", headers={"Origin": "http://localhost:5500"})
        self.assertEqual(
            resp.headers.get("access-control-allow-origin"),
            "http://localhost:5500",
        )

    def test_preflight_for_put_is_allowed(self):
        # 浏览器发 PUT / DELETE 前会先发一个 OPTIONS 预检请求
        resp = self.client.options(
            "/users/1",
            headers={
                "Origin": "http://127.0.0.1:8777",
                "Access-Control-Request-Method": "PUT",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.headers.get("access-control-allow-origin"),
            "http://127.0.0.1:8777",
        )

    def test_request_without_origin_still_works(self):
        # 非浏览器 client（requests / curl / test_client.py）不带 Origin，照常工作
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Hello", resp.json()["message"])


if __name__ == "__main__":
    unittest.main()
