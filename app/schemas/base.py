#!/usr/bin/env python
# encoding: utf-8
"""
Author              : 寂情啊
Date                : 2025-05-16 14:05:48
LastEditors         : 寂情啊
LastEditTime        : 2025-06-20 17:21:24
FilePath            : fast-soy-adminappschemasbase.py
Description         : 说明
倾尽绿蚁花尽开，问潭底剑仙安在哉
"""

from typing import Any, TypeVar, Generic, List
import json
from datetime import datetime, date

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


T = TypeVar("T")


def custom_json_encoder(obj):
    """处理特殊类型的JSON序列化，特别是datetime对象"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class PageData(BaseModel, Generic[T]):
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    records: List[T] = Field(..., description="记录列表")


class Custom(JSONResponse):
    def __init__(
        self,
        code: str | int = "0000",
        status_code: int = 200,
        msg: str = "OK",
        data: Any = None,
        **kwargs,
    ):
        content = {"code": str(code), "msg": msg, "data": data}
        content.update(kwargs)
        # 使用普通初始化，然后在render方法中处理datetime
        super().__init__(content=content, status_code=status_code)

    def render(self, content) -> bytes:
        """重写render方法处理datetime序列化"""
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=custom_json_encoder,  # 使用自定义函数处理datetime
        ).encode("utf-8")


class Success(Custom):
    pass


class Fail(Custom):
    def __init__(
        self,
        code: str | int = "4000",
        msg: str = "OK",
        data: Any = None,
        **kwargs,
    ):
        super().__init__(code=code, msg=msg, data=data, status_code=200, **kwargs)


class SuccessExtra(Custom):
    def __init__(
        self,
        code: str | int = "0000",
        msg: str = "OK",
        data: Any = None,
        total: int = 0,
        current: int | None = 1,
        size: int | None = 20,
        **kwargs,
    ):
        if isinstance(data, dict):
            data.update({"total": total, "current": current, "size": size})
        super().__init__(code=code, msg=msg, data=data, status_code=200, **kwargs)


class CommonIds(BaseModel):
    ids: list[int] = Field(title="通用ids")
