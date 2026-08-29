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
@router.get("/users", response_model=List[UserOut])
def get_users(db: Session = Depends(get_db)):
    # .all() 跟前面用的 .first() 不同，是把符合条件的所有结果都拿出来；
    # 这里没加 .filter()，所以查的是全部用户
    #
    # 注意：这种"返回全部数据"的写法，用户量小时没问题，但真实项目里
    # 数据量大了会很慢——这里先不做分页（pagination），留作认知铺垫
    users = db.query(User).all()
    return users


# 注意路由写法：/users/by-email/{email} —— FastAPI靠URL的具体写法
# （/users/1 vs /users/by-email/xxx@xxx.com）来区分该走哪个路由，不会跟上面的{user_id}搞混
#
# 为什么要单独做这个接口，而不是让前端调用GET /users拿全部数据自己筛选：
# 如果系统里有10万个用户，"下载全部再筛选"要传输10万条数据，非常浪费又慢；
# "在数据库层筛选"不管数据库里有多少条数据，传输的永远只是符合条件的那一条——
# 把"找数据"这件耗资源的事交给专门为此优化过的数据库，而不是丢给前端硬算
@router.get("/users/by-email/{email}", response_model=UserOut)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user