# mp-pdf-bot

公众号文章自动归档为 PDF。基于 [wewe-rss](https://github.com/cooderl/wewe-rss) + headless Chrome。

## 它做什么

- 你订阅一个微信公众号，wewe-rss 帮你持续拉新文章
- 每天 18:00 自动把新文章渲染为 PDF，按公众号归档到 `./pdfs/`

## 依赖

- macOS（仅）
- Homebrew
- Node.js 20+ — `brew install node`
- Google Chrome — `brew install --cask google-chrome`
- git

## 安装

```bash
git clone <this-repo> mp-pdf-bot
cd mp-pdf-bot
./mybot setup
```

`setup` 会：
- 检查依赖
- 把 wewe-rss 克隆到 `./wewe-rss/` 并构建（1-3 分钟）
- 注册 launchd（开机自启 + 崩了重启）
- 加 cron 每天 18:00 跑一次同步
- 装 GUI（菜单栏图标 + Web UI on `localhost:4001`）

完成后：
```bash
./mybot open    # 浏览器自动打开 dashboard
```
- 在 dashboard 里：扫码登录微信读书（**不要勾"24 小时自动退出"**）
- 公众号源 → 添加 → 粘贴公众号任意一篇文章的分享链接

## 使用（朋友视角，零命令行）

装好之后菜单栏会出现一个 **🟢 mp-pdf-bot** 图标。点击它有：

- **Open Dashboard** — 打开 wewe-rss 后台，在这里加公众号、扫码登录微信读书
- **Sync Now** — 立即拉一次新文章并转 PDF
- **Open Web UI** — 打开 mp-pdf-bot 自己的 Web 页面（看状态、看 PDF 列表）
- **Open PDFs Folder** — Finder 打开 PDF 归档目录
- **Stop / Start wewe-rss** — 暂停 / 启动后台服务

或者直接浏览器打开 **http://localhost:4001/** 看 Web UI（有状态条、Sync Now 按钮、按公众号分组的 PDF 列表）。

图标颜色：
- 🟢 服务正常
- 🔴 服务挂了（重启 Mac 通常能自愈，或者菜单栏 → Stop / Start wewe-rss）
- 🔵 正在同步

## 日常使用（命令行）

```bash
./mybot sync         # 立即拉一次新文章并转 PDF
./mybot status       # 查看运行状态
./mybot logs         # tail 服务日志
./mybot open         # 打开 dashboard 添加 / 管理公众号
./mybot stop         # 暂停服务
./mybot start        # 启动服务
./mybot uninstall    # 卸载（保留数据和 PDF）
```

PDF 落到 `./pdfs/<公众号名>/<日期>-<标题>.pdf`。

## 配置

`./mybot setup` 会从 `config.example.env` 生成 `config.env`，可改：

```
WEWE_RSS_PORT=4000               # wewe-rss 监听端口
AUTH_CODE=mp-pdf-bot             # 后台访问密码
PDF_OUTPUT_DIR=./pdfs            # PDF 输出目录
DATA_DIR=./data                  # SQLite 数据库目录
WEWE_RSS_REPO_REF=v2.6.1         # wewe-rss 锁定版本
CRON_TIME="0 18 * * *"           # 自动同步时间（标准 cron 表达式）
```

改完重跑 `./mybot setup` 生效。

## 国内访问

`./mybot setup` 默认用 [npmmirror.com](https://registry.npmmirror.com) 拉 npm 包和 Prisma 二进制，无需 VPN 即可装好。`git clone` wewe-rss 仍直连 github.com — 国内大多数时段 OK，但偶尔抽风。

## 排错

**`./mybot setup` 卡在 git clone**：github.com 抽风。重跑 setup（已 clone 部分会复用），或临时给 git 配代理：
```bash
export ALL_PROXY=socks5://127.0.0.1:7890   # 改成你的代理端口
./mybot setup
```

**`./mybot status` 显示 HTTP 502 / no response**：launchd 没起来。
```bash
./mybot logs   # 看 wewe-rss 报什么错
./mybot stop && ./mybot start
```

**PDF 生成全部失败**：mp.weixin.qq.com 文章 key 过期或被风控。等几小时重试，或在 dashboard 里手动同步一次再 sync。

**微信读书账号被风控**：添加公众号太频繁会被封 24 小时。等就好。

## 卸载

```bash
./mybot uninstall                                  # 拆服务，保留数据
rm -rf data/ pdfs/ config.env                      # 完全清理
```
