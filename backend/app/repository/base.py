import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class SQLAlchemyRepository(Generic[ModelT]):
    """Generic async repository encapsulating persistence for one aggregate type."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def add_all(self, entities: Sequence[ModelT]) -> Sequence[ModelT]:
        self.session.add_all(entities)
        await self.session.flush()
        return entities

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def update(self, entity: ModelT, **values: Any) -> ModelT:
        for key, value in values.items():
            setattr(entity, key, value)
        await self.session.flush()
        return entity

    async def _paginate(self, stmt: Select[Any], limit: int, offset: int) -> tuple[list[ModelT], int]:
        total = await self.session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
        rows = await self.session.scalars(stmt.limit(limit).offset(offset))
        return list(rows.all()), int(total or 0)
