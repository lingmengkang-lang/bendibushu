# 让 GitHub / CNB 自动帮你安装 Ollama + 模型

> 目标：以后你不用在本机手动装 Ollama、手动 `ollama pull`，
> 只要在网页上点一下「运行」，两个平台的自动运行助手就会把引擎和模型装到你这台电脑。

## 一、先回答：能，但必须先做一件事——注册「自托管节点」

两个平台都支持这个能力，但有个关键前提很多人搞错：

| 节点类型 | 跑在哪 | 能装到你的 D:\ 盘吗 | 用途 |
|---|---|---|---|
| **托管 / 云端 runner**（GitHub `ubuntu-latest`、CNB `cnb:arch:amd64`） | 平台临时云机器，跑完即销毁 | **不能** | 只能做云端校验、构建 |
| **自托管 runner / 构建节点** | **你自己的电脑** | **能** | 安装、部署、拉模型 |

所以"交给平台自动助手"的正确姿势是：**把你的 Windows 机器注册成自托管节点**，
之后流水线就在你本机执行，用的是你本机的网络和硬盘——顺便也绕开了本机直连
Ollama CDN 只有 ~5KB/s 的问题吗？**不，绕不开**，模型还是得从 ollama.com 下载。
自托管节点的价值是"自动执行 + 幂等重试 + 全程留日志"，不是加速下载。

> 若你本机网络确实拉不动大模型，可在一台网络正常的机器上装好 Ollama 与模型后，
> 把 `%USERPROFILE%\.ollama\models` 目录整体拷贝到本机同路径（模型按内容寻址，可直接复用）。

## 二、两个平台的分工（本工程已配好）

| 平台 | 配置文件 | 流水线 | 作用 |
|---|---|---|---|
| GitHub | `.github/workflows/setup-ollama.yml` | `validate`（云端） | 仓库结构校验，公开仓库也安全 |
| GitHub | 同上 | `setup-ollama`（自托管 Windows） | 装 Ollama + 拉模型到本机 |
| CNB | `.cnb.yml` | `validate-repo`（云端） | 仓库结构校验 |
| CNB | `.cnb.yml` | `setup-ollama-on-windows-node`（自托管 Windows） | 装 Ollama + 拉模型到本机 |

两个平台调用的都是同一个脚本 `scripts/setup_ollama.ps1`，行为完全一致（幂等，可重复执行）。

## 三、方案 A：注册 GitHub 自托管 runner（一次性，约 5 分钟）

1. 打开仓库页面 → **Settings** → 左侧 **Actions** → **Runners** →
   **New self-hosted runner** → 操作系统选 **Windows**，架构选 **X64**。
   页面会给出下载地址和一条带 `--token` 的注册命令（token 约 1 小时有效，动作要快）。
2. 在本机 PowerShell 里执行（版本号以页面显示的为准）：

```powershell
mkdir D:\actions-runner; cd D:\actions-runner
Invoke-WebRequest -Uri "https://github.com/actions/runner/releases/download/v2.323.0/actions-runner-win-x64-2.323.0.zip" -OutFile runner.zip
Expand-Archive runner.zip -DestinationPath .

# --url 换成你的仓库地址，--token 用页面给的
.\config.cmd --url https://github.com/lingmengkang-lang/bendibushu --token <页面上的TOKEN>

# 提示 "Run as service?" 建议输 Y：开机自启、崩溃自拉起
```

3. 回仓库页面确认 Runner 状态为 **Idle**（在线）。
4. 触发：Actions → `setup-ollama` → **Run workflow** → 可选填模型名 → 运行。

> 注册一次永久有效；换机器/重装系统需要重新注册。

## 四、方案 B：注册 CNB 自托管 Windows 构建节点（一次性）

1. 进入 **根组织 / 组织设置 / 构建节点**，点 **+ 新增 Runner**，填名称，
   标签建议打 `windows`（可再加 `win11`、`gpu` 等，标签是超集匹配）。
2. 点该 Runner 行尾的 **连接指引**，弹窗会给一个 Windows 一键接入脚本
   （已自动注入节点唯一标识，无需手改），在本机 PowerShell 执行。
3. 节点状态变为 **在线** 即接入成功。
4. 之后每次 `git push` 到 main，`setup-ollama-on-windows-node` 流水线就会自动跑。

> CNB 限制（官方文档）：Linux 自托管节点仅支持 arm64；自定义 Runner 无 Docker 环境，
> `runner.cpus` 不生效；机器需能访问 cnb.cool。Windows 节点不受这些限制，正好适合本场景。
> 若组织设置里看不到「构建节点」入口，说明平台未对该组织开放，联系平台管理员。

## 五、验证是否装好

流水线跑完后，本机开一个终端：

```powershell
ollama --version          # 有版本号即引擎 OK
ollama list               # 应看到 qwen2.5:14b 等模型
.\scripts\start.ps1       # 启动服务，11434 应显示"运行中"
```

## 六、安全红线（重要）

**本仓库是公开仓库。公开仓库 + 自托管 runner = 危险组合**：
任何能向你仓库推分支、提 PR 的人，都可以让你的电脑执行任意代码。

因此 GitHub 工作流已做保守默认：`setup-ollama` job 仅在
**workflow_dispatch（网页手动触发）** 时运行，push / PR 不会触发。

如需放开（例如只在你自己一个人的私有仓库用），可修改
`.github/workflows/setup-ollama.yml` 中该 job 的 `if:` 条件，
但请务必确认仓库为私有、或你完全信任所有有推送权限的人。
另外不要把注册 token、仓库 token 写进任何提交到仓库的文件。

CNB 侧流水线 2 已设 `allowFailure: true`：未注册节点时它失败不会拖红云端校验。

## 七、不想用 CI，也可以本机直接跑

```powershell
# 装引擎 + 按 config/ollama-models.txt 拉全部模型
.\scripts\setup_ollama.ps1

# 只拉指定模型
.\scripts\setup_ollama.ps1 -Models "qwen2.5:32b-instruct-q4_K_M,bge-m3"

# 额外拉取视觉模型（图片解析用，best-effort）
.\scripts\setup_ollama.ps1 -PullVision

# 已手动下好 OllamaSetup.exe，走本地安装包（跳过 winget）
.\scripts\setup_ollama.ps1 -InstallerPath D:\Downloads\OllamaSetup.exe

# 只装引擎不拉模型
.\scripts\setup_ollama.ps1 -SkipPull
```

日志会写到 `logs\setup_ollama_<时间戳>.log`，出问题直接看日志。

## 八、常见问题

| 现象 | 原因与处理 |
|---|---|
| 装完提示"找不到 ollama 命令" | winget/安装包不会刷新当前进程 PATH。脚本已自动补 `%LOCALAPPDATA%\Programs\Ollama`；若仍不行，**重开终端**再试 |
| winget 装不上 | 改用手动下载 `https://ollama.com/download`，再用 `-InstallerPath` 指定 |
| 弹出 UAC 授权框 | 安装 Ollama 需要管理员权限，CI 里无人点确认就会超时失败 → 改用 `-InstallerPath` 预装，或以管理员身份本机跑一次 |
| 模型拉取慢/中断 | `ollama pull` 支持断点续传，重跑脚本即可（已拉的模型会跳过） |
| 6GB 显存能跑 32B 吗 | 能跑但会较慢：32B Q4_K_M 仅约 1/4 层进 6GB 显存，其余 CPU 卸载（i7-14650HX 约几 token/s）。默认档即 32B（配 24GB 部署机；该机无独显时接近上限，可改 `qwen2.5:14b-instruct-q6_K`） |
| 内存不足时拉取 32B 会怎样 | 脚本有内存护栏：所需最小内存（32B≈24GB/72B≈48GB）超过物理内存时**自动跳过拉取并提示**，不会下完 20GB 却跑不动。加内存后重跑即可（幂等）。注：16GB 开发/验证机会被护栏自动跳过，属预期行为 |
| CI 里 PowerShell 中文乱码 | 所有 `.ps1` 均带 UTF-8 BOM（`scripts/ci_validate.py` 会校验这一点） |
| 导入知识库时报 `The read operation timed out in upsert` | **嵌入模型没下完**。仅当 `provider=chroma-default` 时首次运行要下载约 80MB 的 `all-MiniLM-L6-v2` 权重，网络不通就会反复重试后超时。本工程默认 `provider=ollama` + `bge-m3`（`setup_ollama.ps1` 会自动拉）不走此路；若坚持用 chroma-default，解法见 `docs/plc/rag_guide.md` 第 4.2 节 |

## 九、装好引擎后：知识库还要再走一步

Ollama 只是推理引擎，知识库导入是另一条链路：

```powershell
.\scripts\start.ps1                                    # 1) 启动 Ollama 服务
python scripts\rag_manager.py add-all                  # 2) 一键导入所有知识目录
python scripts\rag_manager.py scan                     # 3) 确认没有漏入库的文件
python scripts\rag_manager.py search "组态王 命令语言"    # 4) 检索验证
```

> 这两个步骤也可以都写进 CI：把 `add-all` 加到 `.cnb.yml` / workflow 的 self-hosted 阶段即可
> （建议单独一个 job，避免模型没拉完就导入失败）。

## 十、相关文件

- `scripts/setup_ollama.ps1` — 安装 + 拉模型（幂等，两平台共用）
- `.github/workflows/setup-ollama.yml` — GitHub 流水线
- `.cnb.yml` — CNB 流水线
- `scripts/ci_validate.py` — 仓库结构校验（云端门禁）
- `config/ollama-models.txt` — 模型清单（改这里即可改变 CI 拉哪些模型）
- `deploy/install.ps1` — 本机一键部署入口（Python/venv/依赖/自检）
