# 新电脑实时预览交接

> 更新时间：2026-07-19  
> 目标：在另一台电脑恢复 Xixi 项目预览中心，并让思维风暴、码上冒险、公途继续支持实时更新。

## 先理解当前版本状态

GitHub 默认 `git clone` 下载仓库的默认分支，通常是 `main`。

Xixi Dev System 的历史堆叠链是：

1. PR #12：`cx/goal-state-kernel-v1` -> `main`
2. PR #13：`cx/branch-preview-dashboard` -> `main`
3. PR #14：`cx/realtime-preview-v1` -> `main`

截至 2026-07-19，PR #12 与 #13 已进入 `main`，PR #14 是最后一层集成。**从 `main` 读到本文件时，直接使用 `main`，不要再按旧堆叠链切换 Xixi Dev System 分支。** 只有审阅尚未合并的 PR #14 本身时，才使用 `cx/realtime-preview-v1`。

思维风暴、码上冒险和公途是独立仓库，它们的实时预览 PR 有各自的合并状态；Xixi Dev System 进入 `main` 不代表三个项目分支也自动进入各自的默认分支。

## 给另一台电脑 Codex 的交接指令

把下面整段发给另一台电脑上的 Codex：

```text
请恢复我的 Xixi 实时开发预览工作区。以
xixi-dev-system/docs/HANDOFF_NEW_COMPUTER_REALTIME_PREVIEW.zh-CN.md
为唯一交接入口。

Xixi Dev System 使用 main。三个业务项目按各自 PR 的当前状态恢复：
- xixi-dev-system: main
- canvas-storm: cx/direction-workbench-ci（实时预览 PR #4 已合入该分支）
- code-quest: cx/realtime-preview-v1
- gongtu-project: cx/realtime-preview-v1

按交接文档完成安装、依赖准备、项目注册、三项目启动和浏览器验收。
不要覆盖已有工作区，不要提交 .env、API Key、数据库或运行时文件。
遇到问题自行排查并记录证据；只有登录、授权或密钥缺失时再提醒我。
```

## 第一次恢复

下面以 `~/Documents/xixi-workspace` 为新电脑工作目录。目录可调整，但四个仓库不要相互嵌套。

### 1. 安装 Xixi Dev System

```bash
mkdir -p ~/Documents/xixi-workspace
cd ~/Documents/xixi-workspace

git clone https://github.com/xixinikl/xixi-dev-system.git
cd xixi-dev-system
bin/install-local.sh
bin/bootstrap-new-machine.sh --workspace ~/Documents/xixi-workspace
```

如果该电脑已经安装过，使用：

```bash
bin/install-local.sh --upgrade
```

### 2. 拉取三个项目的实时分支

```bash
cd ~/Documents/xixi-workspace

git clone --branch cx/direction-workbench-ci \
  https://github.com/xixinikl/canvas-storm.git
git clone --branch cx/realtime-preview-v1 \
  https://github.com/xixinikl/code-quest.git
git clone --branch cx/realtime-preview-v1 \
  https://github.com/xixinikl/gongtu-project.git
```

私有仓库或协作者仓库 clone 失败时，先确认该电脑已登录有权限的 GitHub 账号。不要改成下载 ZIP；分支、提交和 PR 都依赖 Git。

### 3. 准备运行环境

```bash
XDS="$HOME/.codex/bin/xixi-dev-system"
ROOT="$HOME/Documents/xixi-workspace"

cd "$ROOT/canvas-storm" && npm ci
cd "$ROOT/code-quest" && npm ci
cd "$ROOT/gongtu-project" && npm ci
"$XDS" runtime prepare --project "$ROOT/gongtu-project"
```

`runtime prepare` 只用于适配器中声明了 `{python}` 的 `uv` 隔离运行环境；纯 Node 项目使用对应锁文件的包管理器安装依赖。项目中心也会在首次预览时准备缺失的 Node 依赖，但换机时显式执行更容易定位安装错误。

思维风暴调用真实 AI 时需要本机 `.env`。从 `.env.example` 创建，但不要把旧电脑的 API Key 写进聊天、交接文档或 GitHub：

```bash
cp "$ROOT/canvas-storm/.env.example" "$ROOT/canvas-storm/.env"
```

然后只在新电脑本地填写密钥。没有密钥时，界面和非 AI 流程仍可先验收。

### 4. 注册到项目预览中心

```bash
"$XDS" dashboard register \
  --project "$ROOT/canvas-storm" \
  --id canvas-storm --name "思维风暴" \
  --description "从想法到功能方向的可视化发散工具" \
  --preview-path / --isolation namespace

"$XDS" dashboard register \
  --project "$ROOT/code-quest" \
  --id code-quest --name "码上冒险" \
  --description "面向真实开发能力的互动学习项目" \
  --preview-path / --isolation namespace

"$XDS" dashboard register \
  --project "$ROOT/gongtu-project" \
  --id gongtu --name "公途" \
  --description "公务员备考与练习平台" \
  --preview-path / --isolation namespace

"$XDS" dashboard start --open
```

项目中心会使用新电脑上的空闲端口。端口与旧电脑不同是正常现象，不需要手工改成一致。

## 验收清单

- 项目中心显示思维风暴、码上冒险、公途三个项目。
- 三个项目当前分支都是 `cx/realtime-preview-v1`。
- 三张卡片显示“实时更新”和“打开实时预览”。
- 三个项目能同时启动，网页端口互不相同。
- 码上冒险和公途显示额外 API 端口。
- 修改一个可见文案并保存：码上冒险通过 HMR 更新；思维风暴和公途自动刷新。
- 公途 `/api/health` 返回 200。
- 数据库、日志和 `.env` 没有进入 Git 状态或 GitHub。

## 实时更新的边界

- 新电脑保存本地代码后，新电脑的浏览器会实时更新。
- 两台电脑之间的代码仍通过 `git commit`、`git push`、`git pull` 同步。
- 当前 `127.0.0.1` 只能在本机访问。另一台电脑不能直接打开第一台电脑的 localhost。
- 如果需要“电脑 A 开发、电脑 B 或手机直接观看电脑 A 页面”，应另做带访问控制的局域网/Tailscale 预览，不能直接把开发服务暴露到公网。

## 新项目接入

进入新项目后，对 Codex 说：

```text
把当前项目接入 Xixi 开发系统和实时预览中心。自动识别技术栈，建立
.xixi-dev-system.json，使用动态端口；有数据库或日志时按分支命名空间隔离。
完成依赖准备、项目注册、浏览器实时更新验收和相关测试，不要让我选择内部工具。
```

Codex 应执行以下事实流程：

1. 若不存在适配器，运行 `xixi-dev-system onboard`。
2. 审核自动识别的启动命令和测试命令。
3. 为 Vite/Next 等框架声明 HMR；纯 HTML 或旧项目实现自动刷新。
4. 后端使用额外动态端口，数据库和日志使用分支命名空间。
5. 运行 `runtime prepare` 和项目 doctor。
6. 注册项目中心，启动预览并用浏览器证明文件修改会自动呈现。
7. 将 `.xixi-dev-system.json`、测试和 CI 作为项目代码提交；本机端口、数据库、日志和密钥不提交。

## 当前交付入口（2026-07-19 核验）

- Xixi 实时预览：[PR #14](https://github.com/xixinikl/xixi-dev-system/pull/14)，最终集成到 `main`
- 思维风暴：[PR #4](https://github.com/xixinikl/canvas-storm/pull/4)，已合入 `cx/direction-workbench-ci`
- 码上冒险：[PR #4](https://github.com/xixinikl/code-quest/pull/4)，仍为 draft
- 公途：[PR #20](https://github.com/xixinikl/gongtu-project/pull/20)，仍为 draft

交接以仓库提交、分支、PR 和本文件为事实源，不依赖旧聊天记录。
