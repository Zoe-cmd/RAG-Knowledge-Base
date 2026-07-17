"""
自定义异常与全局异常处理。

定义业务异常类与 FastAPI 异常处理器，
将异常转换为 api-spec.md 中定义的标准错误响应格式。
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.response import error_response

logger = logging.getLogger(__name__)


class APIError(Exception):
    """API 业务异常基类。

    所有业务异常继承此类，由全局异常处理器捕获并转换为标准错误响应。

    Attributes:
        code: 错误码（如 DOCUMENT_NOT_FOUND）
        message: 错误消息
        status_code: HTTP 状态码
        details: 错误详情列表
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: list[dict] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


class ValidationError(APIError):
    """参数验证错误（400）。"""

    def __init__(
        self, message: str = "请求参数验证失败", details: list[dict] | None = None
    ) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details,
        )


class NotFoundError(APIError):
    """资源不存在（404）。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=404)


class DocumentNotFoundError(NotFoundError):
    """文档不存在。"""

    def __init__(self) -> None:
        super().__init__(code="DOCUMENT_NOT_FOUND", message="文档不存在")


class SessionNotFoundError(NotFoundError):
    """会话不存在。"""

    def __init__(self) -> None:
        super().__init__(code="SESSION_NOT_FOUND", message="会话不存在")


class DocumentLimitExceededError(APIError):
    """文档数量超限（409）。"""

    def __init__(self, limit: int) -> None:
        super().__init__(
            code="DOCUMENT_LIMIT_EXCEEDED",
            message=f"文档数量已达上限 {limit}",
            status_code=409,
        )


class FileTooLargeError(APIError):
    """文件过大（413）。"""

    def __init__(self, filename: str, size_mb: float, limit_mb: int) -> None:
        super().__init__(
            code="FILE_TOO_LARGE",
            message=f"文件 {filename} 超过 {limit_mb}MB 限制",
            status_code=413,
            details=[
                {
                    "field": "files",
                    "message": f"文件大小 {size_mb:.1f}MB 超过限制 {limit_mb}MB",
                }
            ],
        )


class UnsupportedFileTypeError(APIError):
    """不支持的文件类型（415）。"""

    def __init__(self, file_type: str, supported: tuple[str, ...]) -> None:
        super().__init__(
            code="UNSUPPORTED_FILE_TYPE",
            message=f"不支持的文件类型: {file_type}",
            status_code=415,
            details=[
                {
                    "field": "files",
                    "message": f"支持的类型: {', '.join(supported)}",
                }
            ],
        )


class ScannedPDFError(APIError):
    """扫描件 PDF（422）。"""

    def __init__(self) -> None:
        super().__init__(
            code="SCANNED_PDF",
            message="该 PDF 为扫描件，MVP 暂不支持，需 OCR",
            status_code=422,
        )


class ServiceUnavailableError(APIError):
    """服务不可用（503）。"""

    def __init__(self, message: str = "服务不可用") -> None:
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=message,
            status_code=503,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。

    将各类异常转换为 api-spec.md 中定义的标准错误响应格式。

    Args:
        app: FastAPI 应用实例
    """

    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, exc: APIError) -> JSONResponse:
        """处理业务 API 异常。"""
        if exc.status_code >= 500:
            logger.error("API 错误: %s", exc, exc_info=True)
        else:
            logger.warning("API 错误 [%s]: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """处理 Pydantic 请求体验证错误。"""
        details = []
        for error in exc.errors():
            details.append(
                {
                    "field": ".".join(str(loc) for loc in error.get("loc", [])),
                    "message": error.get("msg", ""),
                    "type": error.get("type", ""),
                }
            )
        logger.warning("请求验证失败: %s", details)
        return JSONResponse(
            status_code=422,
            content=error_response(
                "VALIDATION_ERROR", "请求参数验证失败", details
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """处理 Starlette HTTP 异常（如 404 路由不存在）。"""
        code_map = {
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            413: "FILE_TOO_LARGE",
            422: "VALIDATION_ERROR",
            500: "INTERNAL_ERROR",
        }
        code = code_map.get(exc.status_code, "ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(code, str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(
        _: Request, exc: Exception
    ) -> JSONResponse:
        """处理未预期的异常（500）。"""
        logger.error("未预期的异常: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=error_response(
                "INTERNAL_ERROR", "服务器内部错误，请稍后重试"
            ),
        )
