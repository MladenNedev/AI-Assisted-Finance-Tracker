from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login() -> dict[str, str]:
    return {"status": "not_implemented"}
