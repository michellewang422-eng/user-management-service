// ============================================================
// api.js —— 几个页面共用的小工具
// login.html 和 index.html 都会先引入这个文件
// ============================================================

// 前端和后端是两个独立的程序。前端通过下面这个地址找后端。
// 后端（uvicorn app.main:app）默认跑在 127.0.0.1:8000。
// 换端口 / 换机器，只改这一行。
const API_BASE = "http://127.0.0.1:8000";

// 读取"当前登录用户"——PR-11 登录成功后，我们把后端返回的整个用户对象
// 用 JSON.stringify 存进了 localStorage 的 "currentUser" 这个键。
// 这里读回来（JSON.parse 转回对象）；没登录就返回 null。
function getCurrentUser() {
  const raw = localStorage.getItem("currentUser");
  return raw ? JSON.parse(raw) : null;
}

// 登出：把登录标记从 localStorage 删掉，回登录页。
// 注意存进 localStorage 的只是 profile、不是真 token，谁都能伪造——
// 和无密码登录一样不安全，真正的 JWT 令牌是以后的 PR 才做。
function logout() {
  localStorage.removeItem("currentUser");
  location.href = "login.html";
}
