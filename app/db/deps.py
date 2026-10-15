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
