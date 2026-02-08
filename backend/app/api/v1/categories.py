from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_category_service, get_current_user
from app.persistence.models import User
from app.schemas.ledger import (
    CategoryCreateRequest,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdateRequest,
)
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryResponse:
    category = await category_service.create_category(
        user_id=current_user.id,
        name=payload.name,
        is_income=payload.is_income,
        color=payload.color,
        icon=payload.icon,
    )
    return CategoryResponse.model_validate(category)


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CategoryListResponse:
    categories, total = await category_service.list_categories(
        user_id=current_user.id, limit=limit, offset=offset
    )
    return CategoryListResponse(
        items=[CategoryResponse.model_validate(category) for category in categories],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryResponse:
    category = await category_service.get_category(category_id, current_user.id)
    return CategoryResponse.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryResponse:
    category = await category_service.update_category(
        category_id=category_id,
        user_id=current_user.id,
        name=payload.name,
        is_income=payload.is_income,
        color=payload.color,
        icon=payload.icon,
    )
    return CategoryResponse.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> Response:
    await category_service.delete_category(category_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
