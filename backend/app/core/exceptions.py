class DomainExceptionError(Exception):
    """Base exception for domain-level failures."""


class AuthenticationError(DomainExceptionError):
    """Raised when authentication fails."""


class ResourceNotFoundError(DomainExceptionError):
    """Raised when a requested resource cannot be found."""


class BudgetExceededError(DomainExceptionError):
    """Raised when a budget limit is exceeded."""
