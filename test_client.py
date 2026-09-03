"""
test_client.py —— 第二个 client：一个纯 Python 脚本，用 requests 库
调用和网页同一套 API，走一遍完整的 CRUD 流程。

对比 user-service-web/（浏览器里的网页 client）：
  - 网页用 JavaScript 的 fetch，这里用 Python 的 requests
  - 网页把登录态存进 localStorage（关 tab 也不掉登录），脚本是一次性的、跑完就退，
    不需要这套 —— "登录态怎么保持"是每个 client 自己的事，做法可以不一样
  - 网页会撞 CORS（浏览器强加给网页 JS 的限制），这个脚本不经过浏览器，没有 CORS 问题
  - 但两者操作的是同一个后端、同一个数据库 —— 这就是"一个后端，多个 client"

用法：
    先启动后端：  uvicorn app.main:app
    再运行本脚本：python test_client.py
"""

import sys
import time

import requests

BASE = "http://127.0.0.1:8000"

# 每次跑用一个带时间戳的邮箱，避免和上次残留的数据撞"邮箱已注册"
EMAIL = f"client-demo-{int(time.time())}@example.com"


def show(step, resp):
    """打印一步的结果：方法 URL -> 状态码 + 响应体"""
    print(f"\n[{step}] {resp.request.method} {resp.request.url}")
    print(f"      -> {resp.status_code}")
    if resp.text:
        print(f"      {resp.text}")


def main():
    session = requests.Session()  # 复用一条连接

    # 1. 注册（POST /users）
    r = session.post(
        f"{BASE}/users",
        json={"email": EMAIL, "first_name": "Client", "last_name": "Demo"},
    )
    show("注册", r)
    r.raise_for_status()
    user_id = r.json()["id"]

    # 2. 登录（POST /auth/login）—— 拿回自己的 profile
    r = session.post(f"{BASE}/auth/login", json={"email": EMAIL})
    show("登录", r)
    r.raise_for_status()
    profile = r.json()
    print(
        f"      登录成功，我是 id={profile['id']} "
        f"{profile['first_name']} {profile['last_name']}"
    )

    # 3. 查自己（GET /users/{id}）
    r = session.get(f"{BASE}/users/{user_id}")
    show("查自己", r)
    r.raise_for_status()

    # 4. 改名（PUT /users/{id}）—— 整体替换，三个字段都要传
    r = session.put(
        f"{BASE}/users/{user_id}",
        json={"email": EMAIL, "first_name": "Client", "last_name": "Renamed"},
    )
    show("改名", r)
    r.raise_for_status()
    print(f"      改完 last_name = {r.json()['last_name']}")

    # 5. 删掉（DELETE /users/{id}）—— 收尾清理；成功是 204、空响应体
    r = session.delete(f"{BASE}/users/{user_id}")
    show("删除", r)
    r.raise_for_status()

    # 6. 再查一次，确认真的没了（预期 404）
    r = session.get(f"{BASE}/users/{user_id}")
    show("删除后再查（预期 404）", r)

    print(
        "\n完整一轮 CRUD 走完。这个脚本和网页操作的是同一个后端、同一个数据库——"
        "\n脚本注册的用户，刷新网页也能看到；反过来也一样。"
    )


if __name__ == "__main__":
    try:
        main()
    except requests.ConnectionError:
        print("连不上后端。先启动：uvicorn app.main:app", file=sys.stderr)
        sys.exit(1)
