from typing import Any, Dict, Optional, Sequence, Type, Union

from fastapi import exceptions, status
from pydantic import BaseModel
from typing_extensions import Annotated, Doc  # type: ignore [attr-defined]


class TooManyRequest(exceptions.HTTPException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self, detail=None, headers=None):
        super().__init__(status_code=self.status_code, detail=detail, headers=headers)


class QuotaLimit(exceptions.HTTPException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    detail = "You have exceeded the allowed API usage limit. Please try again later or contact support if you need further assistance."

    def __init__(self, detail=None, headers=None):
        super().__init__(
            status_code=self.status_code, detail=detail or self.detail, headers=headers
        )


class BadRequest(exceptions.HTTPException):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail=None, headers=None):
        super().__init__(status_code=self.status_code, detail=detail, headers=headers)


class NotFound(exceptions.HTTPException):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, detail=None, headers=None):
        super().__init__(status_code=self.status_code, detail=detail, headers=headers)


class LampValidationError(Exception):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(self, message, extra=None, response=None, status_code=None):
        super().__init__(message)

        self.message = message
        self.extra = extra or {}
        self.response = response
        self.status_code = status_code or status.HTTP_422_UNPROCESSABLE_ENTITY


class LampApplicationError(Exception):
    def __init__(self, message, extra=None, response=None):
        super().__init__(message)

        self.message = message
        self.extra = extra or {}
        self.response = response
