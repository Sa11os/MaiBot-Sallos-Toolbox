"""持久化与宿主桥接共用的外观数据契约。"""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

HexColor = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
REGION_PROPERTIES = {
    "background-color",
    "color",
    "border",
    "border-color",
    "border-width",
    "border-style",
    "border-radius",
    "box-shadow",
    "padding",
    "padding-inline",
    "padding-block",
    "margin",
    "font-weight",
    "font-size",
    "letter-spacing",
    "line-height",
    "text-transform",
}


def validate_declarations(value: str) -> str:
    """限定分区 CSS 为静态声明，服务端和宿主分别校验。"""
    for declaration in value.split(";"):
        if not declaration.strip():
            continue
        name, separator, content = declaration.partition(":")
        if not separator or name.strip() not in REGION_PROPERTIES:
            raise ValueError("分区 CSS 包含未支持的属性")
        if not re.fullmatch(r"[\w\s#.,()%+\-]+", content, flags=re.ASCII):
            raise ValueError("分区 CSS 请使用静态颜色、尺寸与阴影值")
        functions = re.findall(r"([\w-]+)\s*\(", content)
        if any(item.lower() not in {"rgb", "rgba", "hsl", "hsla"} for item in functions):
            raise ValueError("分区 CSS 支持 rgb/rgba/hsl/hsla 颜色函数")
    return value.strip()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RegionStyles(StrictModel):
    sidebar: str = Field(default="", max_length=2000)
    header: str = Field(default="", max_length=2000)
    card: str = Field(default="", max_length=2000)

    _validate = field_validator("sidebar", "header", "card")(validate_declarations)


class AppearanceTheme(StrictModel):
    version: Literal[1] = 1
    name: str = Field(default="我的风格", min_length=1, max_length=40)
    mode: Literal["light", "dark", "system"] = "light"
    primary: HexColor = "#0071E3"
    background: HexColor = "#F5F5F7"
    surface: HexColor = "#FFFFFF"
    text: HexColor = "#1D1D1F"
    muted: HexColor = "#6E6E73"
    border: HexColor = "#D2D2D7"
    sidebar_side: Literal["left", "right"] = "left"
    sidebar_width: int = Field(default=224, ge=160, le=360)
    header_height: int = Field(default=56, ge=48, le=96)
    content_width: int = Field(default=1440, ge=720, le=2560)
    gap: int = Field(default=20, ge=8, le=40)
    font: Literal["system", "serif", "mono"] = "system"
    font_size: int = Field(default=16, ge=14, le=22)
    line_height: float = Field(default=1.6, ge=1.2, le=2.0)
    radius: int = Field(default=16, ge=0, le=24)
    shadow: Literal["none", "soft", "crisp"] = "soft"
    regions: RegionStyles = Field(default_factory=RegionStyles)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("请填写风格名称")
        return value


class SavedPreset(StrictModel):
    id: str = Field(pattern=r"^[a-f0-9]{32}$")
    theme: AppearanceTheme


class PresetState(StrictModel):
    version: Literal[1] = 1
    revision: int = Field(default=0, ge=0)
    presets: list[SavedPreset] = Field(default_factory=list, max_length=50)
