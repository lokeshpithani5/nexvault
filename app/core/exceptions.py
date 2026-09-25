from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class NexvaultException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(NexvaultException):
    def __init__(self, message: str = "Invalid credentials", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHENTICATION_FAILED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class PermissionDeniedError(NexvaultException):
    def __init__(self, message: str = "Permission denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ResourceNotFoundError(NexvaultException):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(NexvaultException):
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class QuorumNotReachedError(NexvaultException):
    def __init__(self, message: str = "Storage quorum could not be satisfied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="QUORUM_NOT_REACHED",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class StorageNodeUnavailableError(NexvaultException):
    def __init__(self, message: str = "Storage node unreachable", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="STORAGE_NODE_UNAVAILABLE",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class DataIntegrityError(NexvaultException):
    def __init__(self, message: str = "Checksum verification failed - data corruption detected", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DATA_INTEGRITY_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(NexvaultException)
    async def nexvault_exception_handler(request: Request, exc: NexvaultException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
                "details": {},
            },
        )
