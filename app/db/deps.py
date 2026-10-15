# 中文导读：
# 请求级数据库会话依赖：为接口提供会话并在请求结束时关闭
# 事务提交由业务层决定，不能把会话关闭当成提交成功

"""Shared FastAPI dependencies.

`get_db` lives here so that every router (auth included) depends on the same
function object. Tests override it once with
`app.dependency_overrides[get_db] = ...`; re-exporting it from a router keeps
the existing import paths working without creating import cycles.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def get_db():
    with SessionLocal() as db:
        yield db


DB = Annotated[Session, Depends(get_db)]
