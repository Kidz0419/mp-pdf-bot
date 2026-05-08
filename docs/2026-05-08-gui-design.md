# mp-pdf-bot GUI — 设计

给非命令行用户用的图形界面：菜单栏图标 + Web UI。装在现有 `mp-pdf-bot` 仓库里。

## 目标场景

- 安装由作者代办（`./mybot setup` 已含 GUI 装配）
- 朋友零命令行：菜单栏图标 + 浏览器页面操作

## 架构

新进程 `mp-pdf-bot-gui`：单 Python 进程，同时跑：

- **rumps** 菜单栏图标（macOS 主线程）
- **Flask** Web UI 服务（后台线程）

复用现有 `mybot` Python 文件里的纯 helper（`sanitize_filename`、`load_config`）和 sync 逻辑（通过 subprocess 调 `./mybot sync`，避免直接 import 冲突）。

由 launchd 管理：开机/登录自启，崩了重启。

## 菜单栏

图标：圆点（颜色映射 wewe-rss 状态）
- 🟢 服务运行中
- 🔴 服务停了
- 🔵 正在 sync

下拉菜单：

```
🟢 mp-pdf-bot
─────────────────
  Open Dashboard       → open http://localhost:4000/dash
  Sync Now             → POST 自身 /api/sync
  Open Web UI          → open http://localhost:4001
  Open PDFs Folder     → open <PDF_OUTPUT_DIR>
─────────────────
  Stop Service         → launchctl bootout wewe-rss agent
  Start Service        → launchctl bootstrap wewe-rss agent
  Quit GUI             → 关闭菜单栏（不影响 wewe-rss 后台）
```

状态轮询：每 5 秒查一次 wewe-rss HTTP，更新图标色。

## Web UI（localhost:4001）

单页 HTML，4 个区块：

1. **Header**：标题 + 当前时间
2. **状态条**：launchd 状态、HTTP 健康、DB 大小、PDF 总数（每 10 秒自动刷新）
3. **操作按钮**：[Sync Now] [Open Dashboard]
4. **PDF 列表**：按公众号分组，可折叠，每篇点击直接在浏览器新标签打开

技术栈：
- 后端：Flask（vanilla，无 ORM、无 blueprint）
- 前端：原生 HTML + 极少 JS（vanilla `fetch` + setInterval 轮询）
- 不用任何前端框架 / 构建工具

## API

```
GET  /                       # 主页面 HTML
GET  /api/status             # JSON: {launchd, http_code, db_kb, pdf_count}
POST /api/sync               # 启动 sync（异步）；返回 {state: "started"}；幂等：已在跑则返回 {state: "running"}
GET  /api/sync/status        # JSON: {state: "idle"|"running", last_result: {ok, fail, skip, finished_at}}
GET  /api/feeds              # JSON: 公众号列表 + 每个的 PDF 文件列表
GET  /pdfs/<path>            # 直接 serve PDF 文件（带 Content-Type, inline）
```

无鉴权（localhost-only）。

## 进程模型

`gui/server.py` 启动顺序：
1. 创建 sync 状态机（线程安全的简单 dict + Lock）
2. Flask app 注册路由
3. 后台线程启动 Flask（threaded=True）
4. 主线程跑 rumps（必须主线程，macOS 限制）
5. rumps 菜单项调用 Flask app 的 `/api/sync` 内部函数（不走 HTTP）

Sync 执行：
- subprocess 调 `<repo>/mybot sync`，stdout/stderr 写到 `logs/sync-gui.log`
- 状态机：idle → running → idle（结果存到 last_result）

## 文件结构

```
mp-pdf-bot/
├── mybot                        # 现有 CLI，不变
├── gui/
│   ├── server.py                # 主入口，~300 行
│   └── web/
│       ├── index.html
│       ├── style.css
│       └── app.js
├── lib/
│   ├── plist_template.xml       # 现有
│   └── gui_plist_template.xml   # 新：GUI 进程 plist
└── requirements-gui.txt         # flask, rumps
```

## 安装流程改动

`mybot setup` 在原有 5 个阶段后，新增 6:

```
== 6. 安装 GUI ==
  - 创建 .venv（python3 -m venv .venv）
  - pip install -r requirements-gui.txt
  - 渲染 gui_plist_template.xml → ~/Library/LaunchAgents/com.mp-pdf-bot.gui.plist
  - xattr -c plist
  - launchctl bootout（如已加载）+ bootstrap
```

`mybot uninstall` 增加：
- bootout + 删 GUI plist
- rm -rf .venv

## 配置（config.env 新增）

```
GUI_PORT=4001     # Web UI 端口
```

## 不做的事（YAGNI）

- 不做 sync 实时进度条（图标变色即可）
- 不做 PDF 预览 / 搜索（浏览器自己看）
- 不做 Web UI 暗色模式（CSS 用 `prefers-color-scheme` 自动跟系统）
- 不做 GUI 鉴权（localhost-only，wewe-rss 自带 AUTH_CODE 防外部）
- 不做多账号
- 不做菜单栏多语言（中文 hardcoded 即可）
- 不做 PDF 删除 / 重命名功能（手 Finder 操作）
- 不做 sync log viewer（直接 `tail -f logs/sync-gui.log`，朋友不会看也无所谓）
- 不打包成 .app（朋友零命令行 = 你装好，不需要 .dmg 分发）
