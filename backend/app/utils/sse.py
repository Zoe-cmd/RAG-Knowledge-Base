"""
SSE（Server-Sent Events）工具。

提供 SSE 事件格式化函数，用于流式问答端点。
SSE 事件格式（DEC-010）:

    event: {event_type}
    data: {json_data}

    （空行结束）

事件类型:
- references: 引用来源（流式开始前发送）
- token: 流式 token（逐个发送）
- done: 完成（含 message_id 与 elapsed_ms）
- error: 错误
"""

import json
from typing import Any


def format_sse_event(event: str, data: Any) -> str:
    """格式化单个 SSE 事件。

    Args:
        event: 事件类型（references/token/done/error）
        data: 事件数据（将被 JSON 序列化）

    Returns:
        SSE 事件字符串（含结尾空行）
    """
    if isinstance(data, str):
        data_str = data
    else:
        data_str = json.dumps(data, ensure_ascii=False)

    return f"event: {event}\ndata: {data_str}\n\n"


def references_event(references: list[dict]) -> str:
    """构造 references 事件。

    Args:
        references: 引用来源列表

    Returns:
        SSE references 事件字符串
    """
    return format_sse_event("references", references)


def token_event(content: str) -> str:
    """构造 token 事件。

    Args:
        content: 本次 token 内容

    Returns:
        SSE token 事件字符串
    """
    return format_sse_event("token", {"content": content})


def done_event(message_id: str, elapsed_ms: int) -> str:
    """构造 done 事件。

    Args:
        message_id: assistant 消息 ID
        elapsed_ms: 流式生成耗时（毫秒）

    Returns:
        SSE done 事件字符串
    """
    return format_sse_event(
        "done", {"message_id": message_id, "elapsed_ms": elapsed_ms}
    )


def error_event(message: str, code: str = "INTERNAL_ERROR") -> str:
    """构造 error 事件。

    Args:
        message: 错误消息
        code: 错误码

    Returns:
        SSE error 事件字符串
    """
    return format_sse_event("error", {"message": message, "code": code})
