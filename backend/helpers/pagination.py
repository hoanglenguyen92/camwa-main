from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int


class PageParams(BaseModel):
    limit: int
    offset: int


def _page_params(
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


PageDep = Annotated[PageParams, Depends(_page_params)]


async def paginate(session: AsyncSession, stmt: Select, schema: type[BaseModel], page: PageParams) -> Page:
    total = await session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = (await session.scalars(stmt.limit(page.limit).offset(page.offset))).all()
    return Page(items=[schema.model_validate(row) for row in rows], total=total or 0)


def page_of(items: list, page: PageParams) -> Page:
    """Pages a list built in Python, for endpoints that compute each row."""
    return Page(items=items[page.offset:page.offset + page.limit], total=len(items))
