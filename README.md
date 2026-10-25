# MaiBot Sallos Toolbox

Sallos 的 MaiBot 工具箱插件，初始版本为 `0.1.0`。

[GitHub 仓库](https://github.com/Sa11os/MaiBot-Sallos-Toolbox) · [问题反馈](https://github.com/Sa11os/MaiBot-Sallos-Toolbox/issues) · [MIT 许可证](LICENSE)

当前提供 `/sallos ping` 命令，用于验证插件加载、配置读取与消息发送链路。后续功能可以继续添加到 `SallosToolboxPlugin`。

## 开发基线

- Python 3.12 或更新版本。
- MaiBot 当前 SDK 架构，初始化对照官方主分支 `1.3.15`。
- 本地开发使用 `maibot-plugin-sdk==2.16.0`。
- Manifest v2，插件 ID 为 `sallos.toolbox`。

版本基线核对日期：2026-10-25。Manifest 的版本区间表达加载策略；实际部署版本请通过宿主联调确认。

## 目录

```text
MaiBot-Sallos-Toolbox/
├── _manifest.json       # 插件身份、兼容范围、业务依赖与能力声明
├── plugin.py            # 配置模型、生命周期、命令、工厂函数
├── pyproject.toml       # 本地代码检查设置
├── requirements-dev.txt # 本地 SDK 和检查工具
├── LICENSE              # MIT 开源许可证
├── README.md
└── .gitignore           # 排除运行时配置、环境与缓存
```

## 本地开发

在项目目录执行 PowerShell 命令：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -c "from plugin import create_plugin; p = create_plugin(); print(p.get_components()); print(p.get_default_config())"
```

最后一条命令验证 SDK 导入、组件声明与默认配置。插件的实际消息收发需要 MaiBot Runner 注入上下文。

## 安装与联调

1. 在 MaiBot 根目录执行 `git clone https://github.com/Sa11os/MaiBot-Sallos-Toolbox.git plugins/MaiBot-Sallos-Toolbox`，让 `_manifest.json` 与 `plugin.py` 位于插件目录根部。
2. 启动 MaiBot，查看日志中的“Sallos 工具箱已加载”。
3. Runner 首次加载会在已安装的插件目录生成 `config.toml`。
4. 在麦麦所在的聊天中发送 `/sallos ping`，预期收到“pong！Sallos 工具箱已就绪喵~”。
5. 修改 `plugin.ping_reply`，等待配置热重载后再次执行命令，确认回复随配置更新。
6. 将 `plugin.enabled` 设为 `false`，确认命令停止发送回复；恢复为 `true` 后继续联调。

默认配置由 `ToolboxConfig` 定义，生成内容如下：

```toml
[plugin]
config_version = "1.0.0"
enabled = true
ping_reply = "pong！Sallos 工具箱已就绪喵~"
```

## 扩展约定

- 用户命令使用 `@Command`，模型工具使用 `@Tool`，流程介入使用 `@HookHandler`。
- 使用 `self.ctx` 调用宿主能力，在 `_manifest.json.capabilities` 中逐项声明所用能力。
- Python 业务依赖放在 `_manifest.json.dependencies`，当前业务依赖为空。
- 保留 `on_load`、`on_unload`、`on_config_update` 与模块级 `create_plugin()`。
- 配置字段提供默认值，结构变化时更新 `plugin.config_version`。
- 持久数据使用 `self.ctx.paths.data_dir`，临时文件使用 `self.ctx.paths.runtime_dir`。

## 开源与发布

作者：[Sallos（Sa11os）](https://github.com/Sa11os)。项目采用 [MIT 许可证](LICENSE)开源。

当前版本为插件开发骨架，已完成代码检查和模拟验证。实际消息收发与配置热重载仍待目标 MaiBot 环境联调；完成后可继续提交至官方插件市场。

## 官方资料

- [插件开发指南](https://docs.mai-mai.org/plugin/)
- [SDK 详细开发指南](https://github.com/Mai-with-u/maibot-plugin-sdk/blob/main/docs/guide.md)
- [Manifest 规范](https://docs.mai-mai.org/plugin/manifest)
- [Vibe Coding 开发约定](https://docs.mai-mai.org/plugin/vibe-coding)
- [官方 MaiBot 依赖与版本](https://github.com/Mai-with-u/MaiBot/blob/main/pyproject.toml)
- [发布插件](https://docs.mai-mai.org/plugin/submission)
