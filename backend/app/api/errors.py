from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import DomainExceptionError
from app.schemas.errors import ErrorResponse


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainExceptionError)
    async def domain_exception_handler(request: Request, exc: DomainExceptionError):
        payload = ErrorResponse(code=exc.code, message=exc.message, details=exc.details)
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        details = None if isinstance(exc.detail, str) else exc.detail
        payload = ErrorResponse(code="http_error", message=message, details=details)
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        payload = ErrorResponse(
            code="validation_error",
            message="Request validation failed",
            details=exc.errors(),
        )
        return JSONResponse(status_code=422, content=payload.model_dump())
