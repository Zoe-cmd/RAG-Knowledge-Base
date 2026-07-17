"""
工具模块包。

提供:
- response: 统一响应格式
- exceptions: 自定义异常与全局异常处理器
- sse: SSE 事件格式化
"""

from app.utils.exceptions import (
    APIError,
    DocumentLimitExceededError,
    DocumentNotFoundError,
    FileTooLargeError,
    NotFoundError,
    ScannedPDFError,
    ServiceUnavailableError,
    SessionNotFoundError,
    UnsupportedFileTypeError,
    ValidationError,
)
from app.utils.response import (
    error_response,
    paginated_response,
    success_response,
)
from app.utils.sse import (
    done_event,
    error_event,
    format_sse_event,
    references_event,
    token_event,
)

__all__ = [
    # response
    "success_response",
    "paginated_response",
    "error_response",
    # exceptions
    "APIError",
    "ValidationError",
    "NotFoundError",
    "DocumentNotFoundError",
    "SessionNotFoundError",
    "DocumentLimitExceededError",
    "FileTooLargeError",
    "UnsupportedFileTypeError",
    "ScannedPDFError",
    "ServiceUnavailableError",
    # sse
    "format_sse_event",
    "references_event",
    "token_event",
    "done_event",
    "error_event",
]
