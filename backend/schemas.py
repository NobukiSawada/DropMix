"""Request bodies for the tool endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PageSpec(BaseModel):
    file_id: str
    index: int = Field(ge=0)
    rotation: int = 0

    @field_validator("rotation")
    @classmethod
    def _rotation_multiple_of_90(cls, v: int) -> int:
        if v % 90:
            raise ValueError("rotation must be a multiple of 90")
        return v % 360


class PagesRequest(BaseModel):
    pages: list[PageSpec] = Field(min_length=1)
    # 出力ファイル名のベース (拡張子なし)。未指定なら先頭ファイル名から生成。
    output_name: str | None = Field(default=None, max_length=120)


class MergeRequest(PagesRequest):
    pass


class SplitRequest(PagesRequest):
    mode: Literal["each", "ranges", "extract"] = "each"
    ranges: str | None = Field(default=None, max_length=1000)


class ImagesRequest(PagesRequest):
    format: Literal["jpg", "png"] = "jpg"
    dpi: int = Field(default=200, ge=36, le=600)
    quality: int = Field(default=90, ge=10, le=100)


class CompressRequest(PagesRequest):
    level: Literal["standard", "strong", "max"] = "standard"


class WatermarkRequest(PagesRequest):
    text: str = Field(min_length=1, max_length=200)
    fontsize: float = Field(default=60, ge=6, le=300)
    opacity: float = Field(default=0.25, ge=0.05, le=1)
    angle: float = Field(default=45, ge=-180, le=180)
    color: str = "#16a34a"


class PageNumbersRequest(PagesRequest):
    position: Literal["bottom-center", "bottom-right", "bottom-left", "top-center", "top-right", "top-left"] = (
        "bottom-center"
    )
    format: str = Field(default="{n} / {total}", max_length=60)
    start: int = Field(default=1, ge=0, le=100000)
    fontsize: float = Field(default=11, ge=6, le=72)
    color: str = "#333333"


class ProtectRequest(PagesRequest):
    user_password: str = Field(min_length=1, max_length=128)
    owner_password: str | None = Field(default=None, max_length=128)
    allow_print: bool = True
    allow_copy: bool = False
    allow_modify: bool = False


class UnlockRequest(BaseModel):
    password: str = Field(max_length=256)
