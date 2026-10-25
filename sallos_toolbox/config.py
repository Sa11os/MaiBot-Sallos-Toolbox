"""工具箱配置；各功能拥有独立配置节。"""

from maibot_sdk import Field, PluginConfigBase


class PluginSettings(PluginConfigBase):
    __ui_label__ = "工具箱"
    config_version: str = Field(default="1.1.0", description="配置结构版本")
    enabled: bool = Field(default=True, description="启用工具箱")
    ping_reply: str = Field(default="pong！Sallos 工具箱已就绪喵~", min_length=1, description="连通检查回复")


class AppearanceSettings(PluginConfigBase):
    __ui_label__ = "外观工作台"
    enabled: bool = Field(default=True, description="启用外观预设管理")


class ToolboxConfig(PluginConfigBase):
    plugin: PluginSettings = Field(default_factory=PluginSettings)
    appearance: AppearanceSettings = Field(default_factory=AppearanceSettings)
