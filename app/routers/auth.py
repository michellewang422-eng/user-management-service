from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, UserOut

# prefix="/auth"：这个 router 里所有路由的路径都会自动加上 "/auth" 前缀，
# 所以下面写 @router.post("/login")，对外实际就是 POST /auth/login。
# 好处：auth 相关的接口都归到 /auth/... 下，不用每个都手写完整路径。
# tags=["auth"]：只影响 /docs 文档页的分组，把这些接口归到 "auth" 这一栏，方便查看。
router = APIRouter(prefix="/auth", tags=["auth"])


# response_model=UserOut：登录成功后，返回这个用户的完整 profile
@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # "登录"本质上在做两件事：
    #   1. 证明"你是谁" —— 这里极度简化，只要 email 在库里就算通过（没有密码校验）
    #   2. 返回和这个身份绑定的数据 —— 也就是这个用户的 profile
    #
    # 这里用的是和 PR-08 一样的"按 email 查"逻辑，但直接在数据库层用 .first()
    # 拿单个对象（而不是去调 GET /users?email= 那个返回数组的接口，再取第一项）
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        # 认证没通过 —— 用 401（"你没能证明你是这个人"），而不是 404
        # （404 是"按 URL 取某个资源、没取到"，语义不符）
        #
        # 学习阶段 detail 写得明确（"邮箱未注册"），方便测试时一眼看懂。
        # 但要知道：真实登录接口不会这么写——如果直接告诉对方"查无此邮箱"，
        # 攻击者就能拿一大堆 email 挨个试、筛出哪些是真实用户（叫"用户枚举"）。
        # 真实系统不管是邮箱不存在还是密码错，都返回同一句模糊提示（如"邮箱或密码不正确"）。
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱未注册",
        )

    # 注意：这个接口能跑通，不代表它安全——任何人知道你的 email 就能"登录"。
    # 这正是后面要加密码哈希、验证码、JWT 令牌的原因。
    return user
