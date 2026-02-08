from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CategoryAlreadyExistsError, CategoryNotFoundError
from app.domain.category import (
    normalize_category_color,
    normalize_category_icon,
    validate_category_name,
)
from app.persistence.models import Category
from app.persistence.repositories import CategoryRepository


class CategoryService:
    def __init__(self, session: AsyncSession, category_repository: CategoryRepository) -> None:
        self.session = session
        self.category_repository = category_repository

    async def create_category(
        self,
        user_id: UUID,
        name: str,
        is_income: bool = False,
        color: str | None = None,
        icon: str | None = None,
    ) -> Category:
        normalized_name = validate_category_name(name)
        if await self.category_repository.get_by_name(user_id, normalized_name):
            raise CategoryAlreadyExistsError("Category already exists")

        try:
            category = await self.category_repository.create(
                user_id=user_id,
                name=normalized_name,
                is_income=is_income,
                color=normalize_category_color(color),
                icon=normalize_category_icon(icon),
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise CategoryAlreadyExistsError("Category already exists") from exc

        await self.session.refresh(category)
        return category

    async def list_categories(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Category], int]:
        categories = await self.category_repository.list_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        total = await self.category_repository.count_by_user(user_id)
        return categories, total

    async def get_category(self, category_id: UUID, user_id: UUID) -> Category:
        category = await self.category_repository.get_by_id(category_id, user_id)
        if category is None:
            raise CategoryNotFoundError("Category not found")
        return category

    async def update_category(
        self,
        category_id: UUID,
        user_id: UUID,
        *,
        name: str | None = None,
        is_income: bool | None = None,
        color: str | None = None,
        icon: str | None = None,
    ) -> Category:
        updates: dict[str, object] = {}
        if name is not None:
            updates["name"] = validate_category_name(name)
        if is_income is not None:
            updates["is_income"] = is_income
        if color is not None:
            updates["color"] = normalize_category_color(color)
        if icon is not None:
            updates["icon"] = normalize_category_icon(icon)

        category = await self.category_repository.update(category_id, user_id, **updates)
        if category is None:
            raise CategoryNotFoundError("Category not found")

        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def delete_category(self, category_id: UUID, user_id: UUID) -> None:
        was_deleted = await self.category_repository.delete(category_id, user_id)
        if not was_deleted:
            raise CategoryNotFoundError("Category not found")
        await self.session.commit()
