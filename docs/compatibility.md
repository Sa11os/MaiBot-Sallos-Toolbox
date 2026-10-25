# 安装兼容与恢复

核对日期：2026-10-25。MaiBot 源码基线 `062d45cf8bd4272ac57d7ec03fcf405e5a458211`，
Dashboard 官方发行包 1.9.9，SDK 2.16.0。

## 支持条件

- MaiBot 提供 WebUI v2 的 custom_pages 与 structured_arguments 能力。
- Dashboard 1.9.9，Python Runner 与 WebUI 访问同一套静态资源。
- Dashboard 目录、入口与专属资源目录允许当前服务用户写入。
- 每个实例使用独立 Dashboard 安装目录。
- 网站从域名根路径提供 Dashboard。独立 CDN、外部前端部署与子路径代理需要单独适配。

目录定位与宿主一致：启用本地 Dashboard 且构建产物存在时使用 dashboard/dist；
其他情况使用 maibot_dashboard.get_dist_path()。版本通过 package.json 或安装包元数据核对。
检测失败时在工作台展示原因，保持预设编辑与保存入口。

静态目录只读时，需要在部署侧调整目录权限或提供可写 Dashboard 目录后重载插件。
主程序升级后重新检查适配；未知 Dashboard 版本保持原版入口。

## 安装与更新

### 0.2.0 配置缺少版本号的恢复

若管理页显示配置缺少 `plugin.config_version`，在现有 `[plugin]` 节补上
`config_version = "1.1.0"` 并保存，保留其他字段。保存后按管理页状态重载插件或重启麦麦。
`1.1.0` 是配置结构版本；插件发行版本使用 `0.2.1`。

0.2.1 的 ZIP 自带完整 `config.toml`，从代码模型默认值生成。已有配置在升级时继续保留，
原有无版本配置需先完成上述修复。通过源码安装时，首次启动前将 `config.example.toml` 复制为
`config.toml`；已有配置按自身内容维护。

ZIP 根目录包含 _manifest.json 与 plugin.py，上传后按宿主提示重启麦麦并启用插件，
然后刷新整个 Dashboard。仅重载插件内页面会继续使用旧的顶层文档。

当前官方 ZIP 安装入口对已安装的插件 ID 返回冲突，请先停用并卸载旧版，再上传新版，
按宿主提示重启。更新前自行备份插件数据目录。

SDK data_dir/appearance/ 下：presets.json 保存个人预设；integration/active.json 保存已应用外观；
integration/backups/ 保存按 SHA256 命名的原始页面入口。

保存预设与应用全站风格分别操作。全站预览和应用同步到此实例的所有浏览器。
图标侧栏收起规则沿用宿主；千禧风格保持图标栏，原版 Dashboard 可使用完整展开宽度。
本版本定制现有布局锚点；新增路由、替换业务组件与任意表单重排可作为后续功能独立开发。

## 首页布局

首页响应式适配由独立 `web/src/shared/dashboard-home.js` 维护，按实际内容区宽度分列。
首页采用全宽，其他页面保留用户设定的内容最大宽度；资讯列表保留独立滚动，首页使用主内容区滚动。
原生编辑模式沿用宿主列宽与行高，完成编辑后恢复响应式显示。卡片顺序和隐藏状态继续生效，
原生列宽与行高设置继续保存，恢复原外观后按宿主设置展示。

## 恢复

1. 工作台点击「恢复原外观」。
2. 标签页应急：在 URL 加 `sallosAppearance=off`，已有查询参数时使用 `&`；
   恢复时改成 `sallosAppearance=on`。Ctrl+Shift+Backspace 也可暂停当前标签页外观。
3. 停用插件会发布恢复状态，并从 index.html 移除插件的精确入口标记。
4. 进程异常退出后，页面在最后一次有效租约后约 30 秒回退。
5. 手动恢复入口：从 index.html 移除 `sallos.toolbox:appearance:v1` 起止注释及其间脚本。
   或核对备份与当前文件后使用备份恢复，保留宿主更新产生的其他改动。

## 接入文件

插件在 Dashboard 下创建 sallos-toolbox-appearance-v1/，包含运行脚本、公开外观状态与所有权标记。
原始入口备份在插件数据目录。配置、聊天数据与个人预设列表保持私有存储。
停用时保留这些资源，供已打开页面读取恢复状态。恢复后的入口停止加载接入脚本。
