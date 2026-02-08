from typing import Any


class DomainExceptionError(Exception):
    status_code = 400
    code = "domain_error"

    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class AuthenticationError(DomainExceptionError):
    status_code = 401
    code = "authentication_error"


class InvalidCredentialsError(AuthenticationError):
    code = "invalid_credentials"


class SessionExpiredError(AuthenticationError):
    code = "session_expired"


class EmailAlreadyExistsError(DomainExceptionError):
    status_code = 409
    code = "email_already_exists"


class ResourceNotFoundError(DomainExceptionError):
    status_code = 404
    code = "resource_not_found"


class BudgetExceededError(DomainExceptionError):
    status_code = 400
    code = "budget_exceeded"
