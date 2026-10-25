# Sallos 工具箱 · MaiBot 插件

让麦麦，更像你的工作台。**0.2.2** 提供全站外观与布局定制，并以独立功能模块承载后续扩展。

[下载插件 ZIP](https://github.com/Sa11os/MaiBot-Sallos-Toolbox/releases) · [问题反馈](https://github.com/Sa11os/MaiBot-Sallos-Toolbox/issues) · [MIT](LICENSE)

## 安装

1. 下载 Release 中的 `MaiBot-Sallos-Toolbox-0.2.2.zip`。
2. 在 MaiBot 插件管理页上传 ZIP，按宿主提示重启麦麦并启用插件。
3. 刷新整个 Dashboard，进入顶部「Sallos 工具箱」→「外观」。
4. 选择模板、调整布局，点击「应用到 Dashboard」并确认。约 2 秒同步到此服务器的浏览器。

**当前适配 Dashboard 1.9.9，开发基线为 MaiBot 1.3.15、SDK 2.16.0、Python 3.12。**
启用时自动检测版本与目录写入权限。目录只读或版本超出适配范围时，工作台显示原因，预设编辑与保存继续可用。
NAS 上的实际版本、权限及反向代理环境请按提示核对。

官方当前 ZIP 安装入口要求先卸载同 ID 的旧插件，再上传新 ZIP。更新前备份插件数据，按管理页提示重启。
详细兼容与恢复说明见 [compatibility.md](docs/compatibility.md)。

## 功能

- Sallos 工作台、纸上书房、午夜终端三套内置风格。
- 全站侧栏左右位置与展开宽度、顶栏高度、内容宽度与留白。
- 六项配色、系统/宋体/等宽字体、字号、行高、圆角与阴影。
- 侧栏、顶栏、卡片的受限 CSS 声明，涵盖静态颜色、尺寸、边框和排版。
- 实时布局示意、对比度提示、全站 20 秒预览与恢复原外观。
- 最多 50 个个人预设；原子保存、并发冲突检查、另存与删除。
- `/sallos ping` 连通检查。

全站应用和预览作用于此服务器的所有 Dashboard 浏览器。个人预设与已应用风格分别保存。
原有功能与导航结构继续保留。千禧风格沿用图标侧栏，使用完整侧栏时可选择「原版 Dashboard」。

## 接入方式

ZIP 提供标准 `_manifest.json`、`plugin.py` 与 `webui.json`，页面使用官方隔离容器和静态 API。
启用时，插件额外备份 Dashboard 的 index.html，加入有明确标记的脚本入口，将脚本与公开外观状态写入专属目录。
停用时撤销入口并发布恢复状态。这属于本插件的兼容层，Dashboard 升级后需要重新检查适配。

多实例共享同一套静态目录时会显示冲突。公开资源仅含当前主题与预览回退主题；个人预设列表及运行配置保留在插件数据目录。
应急恢复：在地址添加 `?sallosAppearance=off` 暂停当前标签页外观，使用 `?sallosAppearance=on` 恢复。
也可按 Ctrl+Shift+Backspace 暂停。插件进程意外退出后，浏览器约 30 秒回退。

## 模块结构

```text
plugin.py                              工厂入口
sallos_toolbox/app.py                   生命周期与装配
sallos_toolbox/config.py                分功能配置
sallos_toolbox/features/health/         连通检查
sallos_toolbox/features/appearance/     模型、组件、服务、预设仓库
  integration/                         检测、文件安装、租约与恢复
web/src/features/appearance/            编辑器、预设、预览与全站脚本
web/src/shared/                         桥接、确认弹窗、风格校验与编译
scripts/                               构建、打包与浏览器验证
tests/                                 模型、并发、SDK 与安装恢复测试
```

新增功能遵循 [开发约束](AGENTS.md) 和 [架构说明](docs/architecture.md)。手写 Python/JS/CSS 文件控制在 300 行以内；生成 HTML 与运行脚本通过构建更新。
视觉参考 SallosWorkbench，结合 Apple Design 和 UI/UX Pro Max 的交互与可访问性原则。

## 本地开发

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python scripts/build_webui.py
.venv/Scripts/python -m unittest discover -s tests -v
.venv/Scripts/python -m ruff check sallos_toolbox scripts tests plugin.py
.venv/Scripts/python scripts/package_plugin.py
```

完整集成验证需要在项目旁放置官方 MaiBot 源码，并下载测试用 Dashboard：

```powershell
.venv/Scripts/python -m pip install --target .dev/dashboard maibot-dashboard==1.9.9
.venv/Scripts/python scripts/browser_smoke.py
```

浏览器验证默认使用本机 Edge。测试使用真实 Dashboard 前端、插件页面和本地插件服务；宿主认证、插件路由与聊天/系统接口使用本地测试替身。测试全过程保持 NAS 环境原样。

## 参考

- [官方插件开发](https://docs.mai-mai.org/plugin/)
- [WebUI 页面协议](https://docs.mai-mai.org/plugin/webui-pages)
- [Manifest 规范](https://docs.mai-mai.org/plugin/manifest)
- [验证记录](docs/verification.md)
