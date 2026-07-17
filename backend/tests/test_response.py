"""
统一响应格式工具单元测试。

测试 success_response、paginated_response、error_response 的输出格式。
"""

from app.utils.response import (
    error_response,
    paginated_response,
    success_response,
)


class TestSuccessResponse:
    """成功响应测试。"""

    def test_single_resource(self):
        """单资源响应。"""
        result = success_response({"id": 1, "name": "test"})
        assert "data" in result
        assert result["data"] == {"id": 1, "name": "test"}
        assert "meta" in result
        assert "requestId" in result["meta"]
        assert not hasattr(result["meta"], "pagination") or "pagination" not in result["meta"]

    def test_collection_resource(self):
        """集合响应（带分页）。"""
        result = success_response([1, 2, 3], pagination={"page": 1})
        assert result["data"] == [1, 2, 3]
        assert "pagination" in result["meta"]
        assert result["meta"]["pagination"] == {"page": 1}

    def test_request_id_is_uuid_format(self):
        """requestId 应为 UUID 格式字符串。"""
        result = success_response({})
        request_id = result["meta"]["requestId"]
        assert isinstance(request_id, str)
        assert len(request_id) == 36  # UUID 字符串长度
        assert request_id.count("-") == 4

    def test_different_request_ids(self):
        """每次调用应生成不同的 requestId。"""
        r1 = success_response({})
        r2 = success_response({})
        assert r1["meta"]["requestId"] != r2["meta"]["requestId"]


class TestPaginatedResponse:
    """分页响应测试。"""

    def test_basic_pagination(self):
        """基本分页响应。"""
        result = paginated_response(
            items=[1, 2, 3], total=10, page=1, size=3
        )
        assert result["data"] == [1, 2, 3]
        assert result["meta"]["pagination"] == {
            "page": 1,
            "size": 3,
            "total": 10,
            "totalPages": 4,  # ceil(10/3) = 4
        }

    def test_single_page(self):
        """单页（总数 <= size）。"""
        result = paginated_response(
            items=[1, 2, 3], total=3, page=1, size=20
        )
        assert result["meta"]["pagination"]["totalPages"] == 1

    def test_empty_list(self):
        """空列表。"""
        result = paginated_response(items=[], total=0, page=1, size=20)
        assert result["data"] == []
        assert result["meta"]["pagination"]["totalPages"] == 0

    def test_last_page(self):
        """最后一页。"""
        result = paginated_response(
            items=[10], total=10, page=4, size=3
        )
        assert result["meta"]["pagination"]["totalPages"] == 4

    def test_total_pages_calculation(self):
        """总页数计算（向上取整）。"""
        # 7 条，每页 3 条 → 3 页
        result = paginated_response(items=[], total=7, page=1, size=3)
        assert result["meta"]["pagination"]["totalPages"] == 3


class TestErrorResponse:
    """错误响应测试。"""

    def test_basic_error(self):
        """基本错误响应。"""
        result = error_response("VALIDATION_ERROR", "参数错误")
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert result["error"]["message"] == "参数错误"
        assert result["error"]["details"] == []
        assert "requestId" in result["meta"]

    def test_error_with_details(self):
        """带详情的错误响应。"""
        details = [{"field": "name", "message": "必填"}]
        result = error_response("VALIDATION_ERROR", "参数错误", details)
        assert result["error"]["details"] == details

    def test_error_details_defaults_to_empty(self):
        """details 默认为空列表。"""
        result = error_response("ERROR", "msg", None)
        assert result["error"]["details"] == []
