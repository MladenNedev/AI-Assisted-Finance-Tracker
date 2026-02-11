from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user, get_transaction_service
from app.core.config import get_settings
from app.persistence.models import User
from app.schemas.ledger import (
    TransactionAttachmentResponse,
    TransactionBulkCategoryRequest,
    TransactionBulkCategoryResponse,
    TransactionCreateRequest,
    TransactionImportResponse,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdateRequest,
    TransferCreateRequest,
    TransferResponse,
)
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    transaction = await transaction_service.create_transaction(
        user_id=current_user.id,
        account_id=payload.account_id,
        category_id=payload.category_id,
        amount=payload.amount,
        direction=payload.direction.value,
        occurred_at=payload.occurred_at,
        merchant=payload.merchant,
        note=payload.note,
        tags=payload.tags,
        splits=payload.splits,
    )
    return TransactionResponse.model_validate(transaction)


@router.post("/transfer", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    payload: TransferCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransferResponse:
    transfer_id, outgoing, incoming = await transaction_service.create_transfer(
        user_id=current_user.id,
        from_account_id=payload.from_account_id,
        to_account_id=payload.to_account_id,
        amount=payload.amount,
        occurred_at=payload.occurred_at,
        note=payload.note,
    )
    return TransferResponse(
        transfer_id=transfer_id,
        outgoing=TransactionResponse.model_validate(outgoing),
        incoming=TransactionResponse.model_validate(incoming),
    )


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    account_id: Annotated[UUID | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
    tag: Annotated[str | None, Query(max_length=32)] = None,
    occurred_from: Annotated[datetime | None, Query()] = None,
    occurred_to: Annotated[datetime | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransactionListResponse:
    transactions, total = await transaction_service.list_transactions(
        user_id=current_user.id,
        account_id=account_id,
        category_id=category_id,
        tag=tag,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        search=search,
        limit=limit,
        offset=offset,
    )
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(transaction) for transaction in transactions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/export", response_class=Response)
async def export_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    account_id: Annotated[UUID | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
    tag: Annotated[str | None, Query(max_length=32)] = None,
    occurred_from: Annotated[datetime | None, Query()] = None,
    occurred_to: Annotated[datetime | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Response:
    csv_payload = await transaction_service.export_transactions_csv(
        user_id=current_user.id,
        account_id=account_id,
        category_id=category_id,
        tag=tag,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        search=search,
        limit=limit,
        offset=offset,
    )
    filename = f"transactions_{current_user.id}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=csv_payload, media_type="text/csv", headers=headers)


@router.post("/import", response_model=TransactionImportResponse)
async def import_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    file: Annotated[UploadFile, File()],
) -> TransactionImportResponse:
    content = await file.read()
    csv_payload = content.decode("utf-8")
    imported, skipped, errors = await transaction_service.import_transactions_csv(
        user_id=current_user.id,
        csv_payload=csv_payload,
    )
    return TransactionImportResponse(imported=imported, skipped=skipped, errors=errors)


@router.get(
    "/{transaction_id}/attachments",
    response_model=list[TransactionAttachmentResponse],
)
async def list_attachments(
    transaction_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> list[TransactionAttachmentResponse]:
    attachments = await transaction_service.list_attachments(current_user.id, transaction_id)
    return [TransactionAttachmentResponse.model_validate(attachment) for attachment in attachments]


@router.post(
    "/{transaction_id}/attachments",
    response_model=TransactionAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    transaction_id: UUID,
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionAttachmentResponse:
    content = await file.read()
    attachment = await transaction_service.create_attachment(
        user_id=current_user.id,
        transaction_id=transaction_id,
        filename=file.filename or "attachment",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    return TransactionAttachmentResponse.model_validate(attachment)


@router.get("/{transaction_id}/attachments/{attachment_id}")
async def download_attachment(
    transaction_id: UUID,
    attachment_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> FileResponse:
    attachment = await transaction_service.get_attachment(
        current_user.id, transaction_id, attachment_id
    )
    settings = get_settings()
    file_path = Path(settings.attachments_dir) / attachment.storage_key
    return FileResponse(
        path=file_path,
        media_type=attachment.content_type,
        filename=attachment.filename,
    )


@router.delete(
    "/{transaction_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_attachment(
    transaction_id: UUID,
    attachment_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> Response:
    await transaction_service.delete_attachment(current_user.id, transaction_id, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bulk-category", response_model=TransactionBulkCategoryResponse)
async def bulk_update_category(
    payload: TransactionBulkCategoryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionBulkCategoryResponse:
    updated = await transaction_service.bulk_update_category(
        user_id=current_user.id,
        transaction_ids=payload.transaction_ids,
        category_id=payload.category_id,
    )
    return TransactionBulkCategoryResponse(updated_count=updated)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    transaction = await transaction_service.get_transaction(transaction_id, current_user.id)
    return TransactionResponse.model_validate(transaction)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    updates = payload.model_dump(exclude_unset=True)
    if "direction" in updates and payload.direction is not None:
        updates["direction"] = payload.direction.value
    transaction = await transaction_service.update_transaction(
        transaction_id=transaction_id, user_id=current_user.id, **updates
    )
    return TransactionResponse.model_validate(transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> Response:
    await transaction_service.delete_transaction(transaction_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
