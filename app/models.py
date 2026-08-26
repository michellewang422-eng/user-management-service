# Column：定义表的一个字段（列）；Integer/String/DateTime：字段的数据类型
from sqlalchemy import Column, Integer, String, DateTime
# func：SQL内置函数工具，这里用来取"当前时间"
from sqlalchemy.sql import func

# 导入database.py里定义好的Base（总登记处），继承它才能被识别成一张数据库表
from app.database import Base


# User类继承Base，SQLAlchemy就知道这个类要对应数据库里的一张表
class User(Base):
    # 明确指定这张表在数据库里叫 "users"
    __tablename__ = "users"

    # id：整数类型，设为主键（primary_key=True）——每一行数据唯一的"身份证号"，自动递增
    id = Column(Integer, primary_key=True)
    # email：字符串类型，unique=True表示不能重复注册，nullable=False表示不能为空
    email = Column(String, unique=True, nullable=False)
    # first_name / last_name：字符串类型，不能为空
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    # created_at：记录创建时间，server_default=func.now()表示不手动传值时，
    # 数据库会自动填入当前时间。这个值一旦写入就不会再变
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # updated_at：记录最近一次被修改的时间。onupdate=func.now()表示每次这条记录
    # 被更新（比如改姓名），SQLAlchemy会自动把这个字段刷新成当前时间
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
