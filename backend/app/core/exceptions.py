"""Domain exceptions, translated into HTTP responses at the API boundary."""


class DomainError(Exception):
    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class AuthenticationError(DomainError):
    status_code = 401
    code = "authentication_failed"


class AuthorizationError(DomainError):
    status_code = 403
    code = "forbidden"


class ValidationError(DomainError):
    status_code = 422
    code = "validation_error"


class ExternalServiceError(DomainError):
    status_code = 502
    code = "external_service_error"
