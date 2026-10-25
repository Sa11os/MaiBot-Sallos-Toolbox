"""MaiBot Runner 入口；业务实现位于 sallos_toolbox 功能包。"""

if __package__:
    from .sallos_toolbox.app import SallosToolboxPlugin
else:
    from sallos_toolbox.app import SallosToolboxPlugin


def create_plugin() -> SallosToolboxPlugin:
    return SallosToolboxPlugin()
