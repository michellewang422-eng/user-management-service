from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut

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