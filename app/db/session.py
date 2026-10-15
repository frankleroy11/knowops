# 中文导读：
# SQLAlchemy 基础模型、连接池与会话工厂
# 数据库连接被多个业务模块复用，具体事务边界由调用方管理

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


s = get_settings()
engine = create_engine(
    URL.create(
        "mysql+pymysql",
        username=s.mysql_user,
        password=s.mysql_password,
        host=s.mysql_host,
        port=s.mysql_port,
        database=s.mysql_database,
    ),
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3, "read_timeout": 5, "write_timeout": 5},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
