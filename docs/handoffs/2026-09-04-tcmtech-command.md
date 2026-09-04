# 2026-09-04 交接：tcmtech 全局启动命令 + AGENTS.md 环境事实固化

## 今日工作概览

1. **/init 维护 AGENTS.md**：把本日 UX 循环交接「环境备注」里的三条持久事实提升进 AGENTS.md（此前只活在 handoff 里）：
   - 8000 端口被另一项目常驻占用、全程不可触碰（原写法是「被占时换端口」的条件式，容易误试 8000）
   - `pnpm build` 在 dev/build 间改写 `frontend/next-env.d.ts` 的 routes 类型路径 → 树脏时 `git checkout -- frontend/next-env.d.ts` 还原，不是代码问题
   - 浏览器自动化在本项目 dev 页面 role 定位点击会假超时（工具行为非产品缺陷，`elementFromPoint` 验证后改 evaluate click）

2. **新增 `tcmtech` 全局终端命令**（需求：输入 tcmtech 即启动本地服务和网页，同终端 Ctrl+C 打断）：
   - 仓库内实现 `scripts/tcmtech.ps1`：复用 `run-internal-preview.ps1`（隔离 runtime、端口占用预检、健康检查、processes.json 登记），默认 BackendPort=8010 / FrontendPort=3000（规避 8000 硬约束），健康检查通过后 `Start-Process` 打开默认浏览器，随后前台阻塞；**Ctrl+C 触发 PowerShell finally → 调 `-Stop` 按进程树停止**
   - runtime 用预览脚本默认 `.tmp/internal-preview`，因此 `pnpm preview:stop` 也能停 tcmtech 起的服务；重跑 `tcmtech` 会先自动停掉上一次服务（预览脚本自带逻辑）
   - 可选参数透传：`-NoBrowser`、`-BackendPort`、`-FrontendPort`、`-RuntimeRoot`、`-AccessToken`、`-OpenTargetsManifestPath`

### 全局 shim（仓库外、机器本地，换机/移仓库需重建）

| 文件 | 服务场景 | 编码注意 |
|------|---------|---------|
| `C:\Users\12035\AppData\Local\Microsoft\WindowsApps\tcmtech.cmd` | 新开的 pwsh / cmd（该目录在用户 PATH；注意 `C:\Users\12035\bin` 不在注册表 PATH，只由 Git Bash profile 注入） | **GBK (cp936) 编码**：cmd 按系统 ANSI/OEM 代码页解析批处理，UTF-8 中文路径会乱码。编辑器里看到「乱码」是正常的，勿按 UTF-8 重写 |
| `C:\Users\12035\bin\tcmtech` | Git Bash（bash shebang 脚本，LF 换行） | UTF-8 即可 |
| `C:\Users\12035\bin\tcmtech.cmd` | pwsh 从 Git Bash 启动（继承 bash PATH）时使用 | 同 GBK。实测 pwsh 同目录优先解析 `.cmd` 而非无扩展名文件 |

shim 内容统一为 `pwsh -NoProfile -ExecutionPolicy Bypass -File "D:\螃蟹's Projects\Tcm_tech\scripts\tcmtech.ps1" %*`（bash 版为 `exec pwsh ... "$@"`）。

踩坑记录：
- D 盘 8.3 短路径生成被禁用（FSO `ShortPath` 返回原中文路径），cmd shim 无法靠短路径规避中文
- pwsh 对 PATH 上无扩展名文件也会做命令解析（Get-Command 能找到）但无法执行 bash shebang 脚本——所以 `~/bin` 里必须同时存在 bash 版与 `.cmd` 版
- 仓库目录一旦移动，三个 shim 全部失效，需按上表重建

## 测试与验证状态

- 启动路径端到端实测：8010 `/health` 200、3000 首页 200，一次通过；`-NoBrowser` 下浏览器步骤跳过
- 分离性实测：强杀 wrapper 后前后端仍存活（分离进程）；`run-internal-preview.ps1 -Stop`（finally 同款命令）杀干净两端、端口释放、processes.json 移除
- **诚实边界**：真实按键 Ctrl+C → finally 是 PowerShell 文档化行为（pipeline stop 展开时保证执行 finally），但本会话无法合成真实控制台 Ctrl+C 信号，按键本身未实测
- 直接**关闭终端窗口**不执行清理、服务残留；恢复手段 = 重跑 `tcmtech`（自动停上次）或 `pnpm preview:stop`
- Windows 终端 Ctrl+D 不是中断键；停止一律用 Ctrl+C

## 转人工 / 遗留

- 无新增转人工项；沿袭同日 UX 循环遗留清单（issue 05 RAG 模板句、/network omics UI 入口、CORS 多端口、AL vs ANL snapshot）
- tcmtech shim 在仓库外，不进任何提交；机器重装或 PATH 变更需按上表重建

## 环境备注

- 测试 runtime 在 `.tmp/internal-preview/`（预览默认根），服务已停、8010/3000 已释放
- 收工时工作树只剩：AGENTS.md 修改、`scripts/tcmtech.ps1` 新增、本 handoff；`frontend/next-env.d.ts` 的 dev 漂移已按惯例 `git checkout` 还原
