"""内置预设作为只读模板提供。"""

from .models import AppearanceTheme


def builtin_presets() -> list[dict]:
    variants = [
        ("workbench", "Sallos 工作台", {}),
        (
            "paper",
            "纸上书房",
            {
                "primary": "#975335",
                "background": "#F4EFE6",
                "surface": "#FFFDF8",
                "text": "#352C23",
                "muted": "#716251",
                "border": "#D7C8B4",
                "font": "serif",
                "radius": 4,
                "shadow": "crisp",
            },
        ),
        (
            "night",
            "午夜终端",
            {
                "mode": "dark",
                "primary": "#8ECCA6",
                "background": "#151D24",
                "surface": "#202B35",
                "text": "#E5EBEF",
                "muted": "#A6B6C4",
                "border": "#4A5D6A",
                "font": "mono",
                "radius": 6,
                "shadow": "none",
            },
        ),
    ]
    return [{"id": key, "theme": AppearanceTheme(name=name, **values).model_dump()} for key, name, values in variants]
