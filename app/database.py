# create_engine：建立数据库连接的核心工具
# sessionmaker：用来创建"会话"（session）——每次读写数据库时，通过会话来操作
# declarative_base：提供一个基础模板，之后定义的表结构类要继承它
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 告诉SQLAlchemy：用SQLite数据库，数据库文件叫 users.db，存在当前项目文件夹下
DATABASE_URL = "sqlite:///./users.db"

# "引擎"：SQLAlchemy跟数据库真正打交道的核心组件，负责建立连接、执行SQL语句
# connect_args={"check_same_thread": False}：SQLite专属设置，允许FastAPI的多个线程共用同一个连接
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# "会话工厂"：之后每次要读写数据库，都通过它创建一个"会话"，相当于一次跟数据库对话的窗口
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# "总登记处"：任何类只要继承了Base（比如以后的User类），SQLAlchemy就会自动记住
# "这个类对应数据库里的哪张表、有哪些字段"，方便之后统一建表
Base = declarative_base()

