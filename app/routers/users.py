from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut
# List：Python的类型注解工具，List[UserOut]表示"一个数组，里面每一项都是UserOut格式"
from typing import List

# APIRouter：FastAPI提供的"迷你app"，先在这里单独定义一堆路由，
# 之后再统一"接入"main.py里的主应用
router = APIRouter()


# response_model=UserOut：告诉FastAPI，这个接口最终返回给前端的数据，
# 必须符合UserOut的格式；FastAPI会自动把返回值转换成UserOut再序列化成JSON
@router.post("/users", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # user: UserCreate —— FastAPI自动读取请求body，用UserCreate这个schema校验格式
    # （不合法直接拒绝，PR-04亲手验证过的机制）
    #
    # db: Session = Depends(get_db) —— 依赖注入：Depends(get_db)告诉FastAPI
    # "调用get_db函数，把它yield出来的数据库会话，作为db传给这个函数"

    # 用会话查一下数据库，看这个email是不是已经被注册过
    # .filter(...)按条件筛选，.first()拿第一条结果，没有就是None
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        # 如果已存在，直接抛出400错误并附带清晰的错误信息，而不是让程序崩溃
        raise HTTPException(status_code=400, detail="邮箱已注册")

    # 用SQLAlchemy的User类（PR-03定义的），造一个新的用户对象
    # 字段从校验过的user（UserCreate对象）里取
    new_user = User(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
    )
    # 把这个新对象"加入"这次会话，先放进"待写入"的队列
    db.add(new_user)
    # 真正把改动写入数据库——新手最容易忘记的一步
    db.commit()
    # commit之后数据库会自动生成id、created_at等字段
    # 这一步把数据库最新的完整数据，重新读回new_user这个对象里
    db.refresh(new_user)

    # 这里返回的new_user是SQLAlchemy的User对象，不是UserOut——
    # User -> UserOut 的转换不是写在这里的显式代码，而是FastAPI在背后自动完成的：
    # 1. 上面@router.post(..., response_model=UserOut) 告诉FastAPI最终要按UserOut格式返回
    # 2. UserOut里的 class Config: from_attributes = True 允许Pydantic
    #    直接从User对象的属性（.id、.email等）读取数据
    # FastAPI拦截这个返回值，自动调用类似UserOut.model_validate(new_user)的操作完成转换，
    # 再序列化成JSON发给前端，这一步对开发者是"隐形"的，不需要手写
    return new_user


# {user_id} 这种花括号写法，声明"这部分URL是一个变量"（路径参数），
# 跟PR-05的"请求体"（body）是不同的传参方式
@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    # 函数参数名user_id要跟URL里的{user_id}完全一致，FastAPI才知道要把URL里的
    # 这部分内容传给这个参数。类型注解: int 会让FastAPI自动把URL字符串转成整数，
    # 如果传的不是数字（比如/users/abc），会自动返回错误，不用自己写转换代码
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # 查不到就返回404，而不是让代码往下跑到return user时
        # 因为user是None而出问题
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


# response_model=List[UserOut]：告诉FastAPI，这次返回值是一个数组，
# 会对数组里每一个用户对象分别做 User -> UserOut 的转换
#
# email: str | None = None —— 可选的query参数，用法是 /users?email=xxx@xxx.com
# 不传就是None，代表不筛选。以后想加更多筛选条件（比如按更新时间），
# 只需要照这个样子再加一个参数，不用为每种筛选单独开一个新接口
#
# 注意：这种"没有筛选条件时返回全部数据"的写法，用户量小时没问题，但真实
# 项目里数据量大了会很慢——这里先不做分页（pagination），留作认知铺垫
@router.get("/users", response_model=List[UserOut])
def get_users(email: str | None = None, db: Session = Depends(get_db)):
    # 先从"查全部用户"这个基础查询开始
    query = db.query(User)

    # 如果传了email，就在基础查询上再加一层筛选条件
    # （因为email是unique的，筛选后最多只会匹配到1条，但返回格式依然是数组）
    if email:
        query = query.filter(User.email == email)

    # .all() 把符合条件的所有结果都拿出来
    users = query.all()

    # 专门针对"按email查、但一个都没查到"这种情况，返回404+清晰提示，
    # 而不是让调用方自己去判断"数组是不是空的"——这样更明确，
    # 不会让人误以为"是不是系统出问题了"。
    # 注意：这里只在"传了email"时才检查，因为没传email时（查全部列表），
    # 结果为空是完全正常的（比如系统里还没有任何用户），不该算错误
    if email and not users:
        raise HTTPException(status_code=404, detail="邮箱未注册")

    return users