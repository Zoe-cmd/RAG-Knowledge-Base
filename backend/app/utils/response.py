"""
统一响应格式工具。

提供成功响应、错误响应、分页元信息的构造函数，
确保所有 API 返回一致的 JSON 结构（符合 api-spec.md 1.3 节）。
"""

import uuid as uuid_module
from typing import Any


def _generate_request_id() -> str:
    """生成请求 ID。"""
    return str(uuid_module.uuid4())


def success_response(
    data: Any,
    pagination: dict | None = None,
) -> dict:
    """构造成功响应。

    Args:
        data: 响应数据（对象或数组）
        pagination: 分页信息（仅集合响应需要）

    Returns:
        标准成功响应字典
    """
    meta: dict[str, Any] = {"requestId": _generate_request_id()}
    if pagination is not None:
        meta["pagination"] = pagination
    return {"data": data, "meta": meta}


def paginated_response(
    items: list,
    total: int,
    page: int,
    size: int,
) -> dict:
    """构造分页集合响应。

    Args:
        items: 当前页数据列表
        total: 总记录数
        page: 当前页码
        size: 每页数量

    Returns:
        标准分页响应字典
    """
    total_pages = (total + size - 1) // size if size > 0 else 0
    return success_response(
        data=items,
        pagination={
            "page": page,
            "size": size,
            "total": total,
            "totalPages": total_pages,
        },
    )


def error_response(
    code: str,
    message: str,
    details: list | None = None,
) -> dict:
    """构造错误响应。

    Args:
        code: 错误码（如 VALIDATION_ERROR）
        message: 人类可读的错误消息
        details: 错误详情列表

    Returns:
        标准错误响应字典
    """
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        },
        "meta": {"requestId": _generate_request_id()},
    }
