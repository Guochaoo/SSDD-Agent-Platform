# RSOD 智能目标检测平台 Git 日常协作操作指南

这份文档面向第一次参与多人 Git 项目的同学，命令已经按照本项目的实际仓库和分支关系编写。

## 1. 先认识本项目的三个位置

本项目的代码实际上保存在三个位置：

```text
你的电脑（本地仓库）
    │
    ├── origin：你的 GitHub Fork
    │      SmithLili/xjtucs_shixun_group19
    │
    └── upstream：组长的 GitHub 仓库
           Guochaoo/xjtucs_shixun_group19
```

在当前项目中：

```text
origin   = git@github.com:SmithLili/xjtucs_shixun_group19.git
upstream = git@github.com:Guochaoo/xjtucs_shixun_group19.git
```

- `origin` 是你自己的 Fork。你有权限把个人分支推送到这里。
- `upstream` 是组长的仓库。团队最新代码在它的 `dev` 分支中。
- 本地 `dev` 是组长 `upstream/dev` 在你电脑上的副本。
- 功能分支是你实际编写代码的地方，例如 `codex/frontend-b-history-filter`。

可以用下面的命令随时检查仓库地址：

```powershell
git remote -v
```

## 2. 什么是分支

可以把分支理解为“同一个项目在某个时刻分出来的一条开发路线”。

它不是在硬盘里复制了几个完整项目文件夹。Git 只保存不同版本之间的提交和差异，然后根据当前分支把工作区文件切换成相应版本。

例如：

```text
组长 dev
    │
    ├── codex/frontend-b-history-filter
    │       └── 历史记录筛选修改
    │
    └── codex/frontend-a-agent-chat
            └── 智能对话修改
```

两个功能分支通常不是包含关系，而是从同一个 `dev` 分出来，分别完成不同功能，最后通过 Pull Request 合并回组长的 `dev`。

查看当前所有本地分支：

```powershell
git branch
```

带 `*` 的分支就是当前分支。

只查看当前分支名称：

```powershell
git branch --show-current
```

查看本地分支、最新提交以及跟踪的远程分支：

```powershell
git branch -vv
```

## 3. 每天开始工作前的标准流程

### 第一步：进入项目根目录

```powershell
cd C:\Users\dogDragon\OneDrive\Desktop\rsod-agent-platform
```

后续 Git 命令最好都在这个目录执行。

### 第二步：检查当前状态

```powershell
git status
```

这个命令会告诉你：

- 当前在哪个分支；
- 哪些文件已修改；
- 哪些文件还没有提交；
- 是否正在合并或解决冲突。

如果显示：

```text
nothing to commit, working tree clean
```

说明工作区干净，可以安全切换分支。

如果有未提交修改，先不要直接切换到 `dev`。请先参考本文“未完成代码如何临时保存”一节。

### 第三步：切换到本地 dev

```powershell
git switch dev
```

含义：让当前工作区显示本地 `dev` 分支的代码。

### 第四步：获取组长仓库的最新信息

```powershell
git fetch upstream
```

含义：把组长仓库各分支的最新提交信息下载到本地，但暂时不修改当前文件。

执行后，`upstream/dev` 表示“刚刚获取到的组长最新 dev”。

可以检查组长是否有新提交：

```powershell
git log --oneline HEAD..upstream/dev
```

- 没有输出：本地 `dev` 已经是最新的。
- 有提交输出：组长仓库比本地 `dev` 更新。

### 第五步：安全更新本地 dev

```powershell
git merge --ff-only upstream/dev
```

含义：只允许本地 `dev` 快进到组长的最新 `dev`，不会偷偷产生额外的合并提交。

常见输出：

```text
Already up to date.
```

表示本地已经是最新版本。

如果显示 `Fast-forward`，表示成功下载并更新了组长的新代码。

### 第六步：进入自己的功能分支

如果是继续昨天的任务：

```powershell
git switch codex/frontend-b-具体功能名
```

例如：

```powershell
git switch codex/frontend-b-data-integration
```

然后把刚更新的本地 `dev` 合入功能分支：

```powershell
git merge dev
```

含义：在保留自己功能代码的同时，同步团队最新修改。

如果这是一个全新的任务，应从最新 `dev` 创建新分支：

```powershell
git switch -c codex/frontend-b-具体功能名
```

例如：

```powershell
git switch -c codex/frontend-b-dashboard-task-type
```

`-c` 表示创建并立即切换到新分支。

不要为两个互不相关的功能长期共用一个分支。一个分支最好对应一个任务和一个 PR。

### 每天开始工作的命令速查

继续已有功能分支时：

```powershell
cd C:\Users\dogDragon\OneDrive\Desktop\rsod-agent-platform
git status
git switch dev
git fetch upstream
git merge --ff-only upstream/dev
git switch codex/frontend-b-具体功能名
git merge dev
```

开始全新任务时：

```powershell
cd C:\Users\dogDragon\OneDrive\Desktop\rsod-agent-platform
git status
git switch dev
git fetch upstream
git merge --ff-only upstream/dev
git switch -c codex/frontend-b-具体功能名
```

## 4. 开发过程中怎么查看修改

查看简短状态：

```powershell
git status --short
```

查看尚未暂存的具体代码差异：

```powershell
git diff
```

只查看前端目录的差异：

```powershell
git diff -- frontend
```

建议开发一小段后就查看一次，不要等到最后才发现改了不相关文件。

## 5. 工作完成后如何提交

Git 的提交分为三步：暂存、提交、推送。

```text
工作区文件
   │ git add
   ▼
暂存区
   │ git commit
   ▼
本地提交
   │ git push
   ▼
你的 GitHub Fork（origin）
```

### 第一步：确认当前在个人功能分支

```powershell
git branch --show-current
```

应该看到类似：

```text
codex/frontend-b-dashboard-task-type
```

如果显示 `dev`，不要直接提交功能代码，应先创建或切换到个人功能分支。

### 第二步：查看准备提交的文件

```powershell
git status
```

前端 B 一般只提交 `frontend` 内与当前任务有关的文件。

### 第三步：把需要的文件加入暂存区

推荐精确添加文件：

```powershell
git add frontend/src/views/HistoryPage.vue
git add frontend/src/api/history.js
git add frontend/tests/api/history.test.js
```

如果确认整个前端目录的修改都属于这次任务，也可以：

```powershell
git add frontend
```

不建议习惯性使用：

```powershell
git add .
```

因为它可能把测试数据库、日志、安装包和不相关后端修改一起放进提交。

### 第四步：检查暂存区内容

```powershell
git diff --cached
```

含义：查看下一次 `commit` 真正会包含哪些代码。

也可以只看文件列表：

```powershell
git diff --cached --stat
```

如果误加了某个文件，可以取消暂存，但保留文件修改：

```powershell
git restore --staged 文件路径
```

例如：

```powershell
git restore --staged backend/test.db
```

### 第五步：运行必要验证

前端测试：

```powershell
cd frontend
npm run test:run
```

前端正式构建：

```powershell
npm run build
```

运行结束后回到项目根目录：

```powershell
cd ..
```

### 第六步：创建本地提交

```powershell
git commit -m "feat(frontend): 补充历史记录时间筛选"
```

`commit` 只会保存到本地 Git 仓库，不会自动上传 GitHub。

常用提交类型：

- `feat`：新增功能；
- `fix`：修复问题；
- `test`：补充测试；
- `docs`：修改文档；
- `refactor`：重构但不改变功能；
- `chore`：配置、依赖等维护工作。

例子：

```powershell
git commit -m "fix(frontend): 修复 ZIP 历史记录类型显示"
git commit -m "test(frontend): 补充数据看板接口测试"
git commit -m "docs: 添加 Git 日常协作指南"
```

### 第七步：推送到自己的 Fork

第一次推送新分支：

```powershell
git push -u origin codex/frontend-b-具体功能名
```

例如：

```powershell
git push -u origin codex/frontend-b-dashboard-task-type
```

- `push`：把本地提交上传到远程仓库；
- `origin`：你的 Fork；
- `-u`：建立本地分支与远程分支的跟踪关系。

设置过 `-u` 后，这个分支以后只需要：

```powershell
git push
```

## 6. 如何创建 Pull Request

推送成功后，进入 GitHub：

```text
https://github.com/SmithLili/xjtucs_shixun_group19
```

点击 `Compare & pull request`，或者进入 `Pull requests` 后点击 `New pull request`。

PR 方向必须是：

```text
base repository：Guochaoo/xjtucs_shixun_group19
base branch：dev

head repository：SmithLili/xjtucs_shixun_group19
compare branch：codex/frontend-b-具体功能名
```

人话解释：

```text
把你 Fork 中的个人功能分支
合并到组长仓库的 dev 分支
```

不要把目标分支选成组长的 `main`，也不要把 PR 提到自己 Fork 的 `main`。

PR 标题示例：

```text
feat(frontend): 补充数据看板任务类型分布
```

PR 描述建议包含：

```markdown
## 完成内容

- 增加任务类型分布图表
- 接入真实统计接口
- 增加空数据和接口错误状态

## 验证情况

- npm run test:run 通过
- npm run build 通过

## 影响范围

- 仅修改前端 B 数据看板相关代码
```

创建 PR 不等于代码已经进入组长仓库。只有组长审核并点击 Merge 后，代码才真正进入 `upstream/dev`。

## 7. PR 提出后又需要修改怎么办

不需要重新创建分支，也不需要重新创建 PR。

继续在原功能分支修改，然后执行：

```powershell
git add 具体文件
git commit -m "fix(frontend): 根据评审意见调整看板"
git push
```

新的提交会自动出现在原来的 PR 中。

## 8. PR 合并后的收尾流程

组长合并 PR 后，先更新本地 `dev`：

```powershell
git switch dev
git fetch upstream
git merge --ff-only upstream/dev
```

确认功能分支确实已经合并后，可以删除本地旧分支：

```powershell
git branch -d codex/frontend-b-具体功能名
```

删除你 Fork 上的远程旧分支：

```powershell
git push origin --delete codex/frontend-b-具体功能名
```

删除分支不会删除已经合入 `dev` 的代码。

## 9. 未完成的代码如何临时保存

如果代码只写了一半，又必须切换分支，可以使用 `stash`。

临时保存当前修改：

```powershell
git stash push -m "前端B历史筛选开发中"
```

然后可以安全切换和更新 `dev`。

返回原功能分支后恢复修改：

```powershell
git switch codex/frontend-b-具体功能名
git stash pop
```

查看所有临时保存：

```powershell
git stash list
```

如果修改已经形成一个可说明的阶段，也可以直接在个人功能分支创建本地提交，不必强制使用 stash。

## 10. 同步 dev 时出现冲突怎么办

在功能分支执行：

```powershell
git merge dev
```

如果 Git 显示 `CONFLICT`，说明你和其他同学修改了同一文件的相同位置。

第一步，查看冲突文件：

```powershell
git status
```

第二步，打开冲突文件，会看到：

```text
<<<<<<< HEAD
你的功能分支代码
=======
dev 中其他同学的代码
>>>>>>> dev
```

人工保留正确内容，并删除这些冲突标记。

第三步，标记为已解决：

```powershell
git add 冲突文件路径
```

第四步，完成合并提交：

```powershell
git commit -m "merge: 同步最新 dev 并解决冲突"
```

如果还没有解决任何冲突，并且决定取消本次合并：

```powershell
git merge --abort
```

不要在不了解影响时执行 `git reset --hard`，它可能直接丢弃本地修改。

## 11. git fetch 和 git pull 的区别

### git fetch upstream

```powershell
git fetch upstream
```

只下载组长仓库的最新提交信息，不改动当前工作区，适合先检查再决定如何合并。

### git pull

`git pull` 基本相当于：

```text
git fetch
    +
git merge（或配置的 rebase）
```

它会下载后立即合并到“当前所在分支”。如果忘记自己正在哪个分支，就可能把代码合到错误位置。

本项目为了更清楚和安全，推荐更新组长 `dev` 时使用：

```powershell
git switch dev
git fetch upstream
git merge --ff-only upstream/dev
```

而不是在个人功能分支里直接执行：

```powershell
git pull upstream dev
```

## 12. 不应提交的本地文件

下面这些通常只属于个人电脑，不应进入 PR：

```text
.venv/
.vscode/
node_modules/
dist/
backend/logs/
*.log
*.db
*.whl
.env
datasets/
runs/
*.pt
*.onnx
```

提交前务必使用：

```powershell
git status
git diff --cached --stat
```

确认没有把这些文件放入暂存区。

## 13. 常用检查命令

查看当前状态：

```powershell
git status
```

查看当前分支：

```powershell
git branch --show-current
```

查看所有本地和远程分支：

```powershell
git branch -a
```

查看远程仓库地址：

```powershell
git remote -v
```

查看最近提交：

```powershell
git log --oneline --decorate -10
```

查看分支关系图：

```powershell
git log --oneline --graph --decorate --all --max-count=30
```

查看本地比组长 dev 落后哪些提交：

```powershell
git log --oneline HEAD..upstream/dev
```

查看当前分支比组长 dev 多出的提交：

```powershell
git log --oneline upstream/dev..HEAD
```

查看当前分支相对组长 dev 修改了哪些文件：

```powershell
git diff --stat upstream/dev...HEAD
```

## 14. 最简日常流程卡片

### 每天开始

```powershell
cd C:\Users\dogDragon\OneDrive\Desktop\rsod-agent-platform
git status
git switch dev
git fetch upstream
git merge --ff-only upstream/dev
git switch codex/frontend-b-具体功能名
git merge dev
```

### 完成工作

```powershell
git status
git add frontend/具体文件
git diff --cached --stat
cd frontend
npm run test:run
npm run build
cd ..
git commit -m "feat(frontend): 简要说明本次工作"
git push -u origin codex/frontend-b-具体功能名
```

第一次推送使用 `git push -u origin 分支名`，后续更新同一个 PR 只需要：

```powershell
git push
```

最后在 GitHub 创建：

```text
SmithLili/xjtucs_shixun_group19:个人功能分支
                         ↓ Pull Request
Guochaoo/xjtucs_shixun_group19:dev
```

