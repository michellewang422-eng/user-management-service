# datetime：Python内置的日期时间类型，用来给created_at/updated_at做类型标注
from datetime import datetime

# BaseModel：Pydantic所有校验模型的基础类，任何schema都要继承它
# EmailStr：专门校验"这是不是一个合法邮箱格式"的类型
from pydantic import BaseModel, EmailStr


# UserCreate：定义"创建用户"时，前端传进来的数据该长什么样
# 只有三个字段，不含id/created_at/updated_at——这些是数据库自动生成的，不该由前端传入
class UserCreate(BaseModel):
    email: EmailStr        # 类型注解：必须是合法邮箱格式，否则Pydantic自动拒绝
    first_name: str
    last_name: str


# UserOut：定义"返回给前端"的数据该长什么样，包含数据库生成的全部字段
class UserOut(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        # from_attributes = True：允许Pydantic直接从SQLAlchemy的User对象属性
        # （比如 .id、.email）里读取数据，而不是只认字典格式
        # 没有这行，PR-05返回数据库查询结果时会报错
        from_attributes = True


# LoginRequest：定义"登录"时前端传进来的数据。
# 这个简化版登录只有 email 一个字段、没有密码——正因为如此它并不安全：
# 任何人只要知道你的 email 就能"登录"进你的账号。以后加密码/验证码/JWT
# 就是为了堵这个漏洞。
class LoginRequest(BaseModel):
    email: EmailStr
