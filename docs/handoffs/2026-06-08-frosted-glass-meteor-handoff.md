# Handoff — 前端毛玻璃 + 流星 UI 收尾

> 日期：2026-06-08
> 接手：GPT (Codex CLI / Cursor / Windsurf)
> 分支：`feat/multilingual-bge-m3-backend`
> 移交人：用户 + Claude (Hermes Agent)

> Superseded note（2026-06-08）：本 handoff 记录的是 UI 收尾中途状态，后续已由
> `docs/handoffs/2026-06-08-post-frontend-ui-handoff.md` 取代。最新事实是用户已确认
> “目前前端做成这样就很好了”，相关前端 commits 已推送；本文件仅作历史参考，不再作为当前执行入口。

---

## 一句话目标

把 `f878784 feat(frontend): refine meteor shower and frosted glass surfaces` 这次视觉改造**收尾并 push**。代码已落地、门禁全绿，唯一缺的是**用户对流星动效的最终拍板**与（可能的）一两个微调，然后 `git push origin feat/multilingual-bge-m3-backend`。

不要把这条收尾扩成"再来一轮重做"。改动范围已经定型，只剩"看实机、按用户反馈微调、push"。

---

## 当前 git 状态（务必先确认一致）

```
On branch feat/multilingual-bge-m3-backend
Your branch is ahead of 'origin/feat/multilingual-bge-m3-backend' by 2 commits.

Changes not staged for commit:
  modified:   frontend/next-env.d.ts        ← 自动生成，不要 commit

Untracked files:
  论文产出/                                  ← 不属于这条任务，别动
  项目实体/                                  ← 不属于这条任务，别动
```

待 push 的两个 commit：

| Commit | 摘要 | 角色 |
|---|---|---|
| `24b0d78` | feat(frontend): add persistent workbench shell UI | 上一次会话已落地的左侧栏壳子，**不要回滚** |
| `f878784` | feat(frontend): refine meteor shower and frosted glass surfaces | 本次毛玻璃 + 流星重做，**收尾对象** |

### ⚠️ 三个不要碰

1. **`frontend/next-env.d.ts`** 的 `.next/dev/types/routes.d.ts` 改动是 `next dev` 自动重写出来的，**不要 add/commit**。push 前用 `git checkout -- frontend/next-env.d.ts` 还原。
2. **`论文产出/`** 与 **`项目实体/`** 是另一条工作流（论文产出），由用户主线推进，**不要 git add，也不要 rm**。两个目录已经在 `.gitignore` 之外但属于本地 worktree 文档。
3. **不要改 `services/rag.py`、disclaimer 字符串、品牌 token**——见下方"项目锁定项"。

---

## 已完成的改动（f878784 内容速查）

文件清单（14 个文件，+375/-218）：

```
frontend/app/workbench.css                         主战场
frontend/components/DemoDataBanner.tsx             加 backdropFilter
frontend/components/EntityChips.tsx                加 backdropFilter
frontend/components/LiteratureDataSourceBanner.tsx 加 backdropFilter
frontend/components/LiteraturePdfUploadClient.tsx  加 backdropFilter
frontend/components/LiteratureSearchClient.tsx     加 backdropFilter
frontend/components/RagEvalReportClient.tsx        加 backdropFilter
frontend/components/WorkbenchShell.tsx             流星 div × 8
frontend/lib/ui/status-card.ts                     blur 14px / saturate 135%
frontend/lib/ui/surfaces.ts                        blur 22~24px / saturate 150~155%
frontend/next-env.d.ts                             被 next dev 顺手改，已收进 commit
frontend/tests/page-shell-consistency.test.ts      正则断言对齐新值
frontend/tests/status-card.test.ts                 deepEqual 对齐
frontend/tests/surfaces.test.ts                    deepEqual 对齐
```

### 视觉关键数值（已落地）

| 项 | 值 | 位置 |
|---|---|---|
| `--qiyan-glass-bg` | `rgba(6, 14, 24, 0.18)` | [workbench.css:20](../../frontend/app/workbench.css#L20) |
| `--qiyan-glass-bg-strong` | `rgba(7, 16, 27, 0.28)` | [workbench.css:21](../../frontend/app/workbench.css#L21) |
| `--qiyan-glass-bg-soft` | `rgba(7, 16, 27, 0.12)` | [workbench.css:22](../../frontend/app/workbench.css#L22) |
| `--qiyan-glass-filter` | `blur(24px) saturate(150%)` | [workbench.css:24](../../frontend/app/workbench.css#L24) |
| `.workbench-page::after` opacity | `0.72`（首页用）| [workbench.css:87](../../frontend/app/workbench.css#L87) |
| `.workbench-page:not(.home-page)::after` opacity | **`0.86`**（内页用，**用户标记为可能偏暗**）| [workbench.css:104-106](../../frontend/app/workbench.css#L104-L106) |
| `.meteor` 头部 box-shadow | 3 层 6/16/30px 发光 | [workbench.css:1212-1215](../../frontend/app/workbench.css#L1212-L1215) |
| `.meteor::before` 尾长 | `clamp(220px, 26vw, 420px)` | [workbench.css:1225](../../frontend/app/workbench.css#L1225) |
| `@keyframes meteorFall` | 0→14% 淡入 + scaleX 0.4→1.0，70%→100% 淡出 | [workbench.css:1276-1299](../../frontend/app/workbench.css#L1276-L1299) |
| `.meteor:nth-child(1..8)` | 8 个流星，周期 7.6~12.4s，错相位 | [workbench.css:1301-1355](../../frontend/app/workbench.css#L1301-L1355) |

---

## 待办（按优先级）

### 1. 先看实机（必须，截图抓不到动画）

```powershell
# 假设后端已经在 127.0.0.1:8000，否则先起后端
cd frontend
pnpm install        # 如果未装依赖
pnpm dev            # http://localhost:3000
```

浏览器开 `/`（首页）和 `/literature`、`/rag` 任一内页，**观察**：

- 流星是否如用户预期的"明亮头 + 长拖尾 + 平滑淡入淡出"
- 内页毛玻璃面板是否仍能透出星空（不应该糊成一片黑）
- 内页背景是否偏暗（`::after` opacity 0.86 是用户标的可疑点）

### 2. 找用户拍板

用户偏好简体中文 + 直接列项。问法建议：

> 流星动效现在是这样（截图/录屏附上），1) 头亮度可以吗？2) 尾长可以吗？3) 淡入淡出节奏可以吗？4) 内页 `::after` opacity 0.86 要不要降到 0.7？

### 3. 按反馈微调（如果有）

常见微调点速查：

| 用户反馈 | 改哪里 |
|---|---|
| 流星太多 / 太密 | [WorkbenchShell.tsx:46-53](../../frontend/components/WorkbenchShell.tsx#L46-L53) 删一两个 div + 同步删 [workbench.css:1301-1355](../../frontend/app/workbench.css#L1301-L1355) 对应的 `:nth-child()` |
| 流星太亮 | [workbench.css:1212-1215](../../frontend/app/workbench.css#L1212-L1215) box-shadow 三档 rgba alpha 同比降 |
| 拖尾太长 | [workbench.css:1225](../../frontend/app/workbench.css#L1225) clamp 上下限调小 |
| 内页太暗 | [workbench.css:105](../../frontend/app/workbench.css#L105) `opacity: 0.86` → `0.7` 左右 |
| 面板太透 / 内容看不清 | `--qiyan-glass-bg` 的 0.18 ↑ 到 0.24~0.30；连带 [workbench.css:20-22](../../frontend/app/workbench.css#L20-L22) |

**注意**：任何改动后必须跑下方"门禁"，因为 [page-shell-consistency.test.ts:32-42](../../frontend/tests/page-shell-consistency.test.ts#L32-L42) 用正则断言锁了 `--qiyan-glass-bg` / `meteorFall` / `qiyanStarDrift` 这些名字。改名要同步改测试，改数值不会断（除非数值进入测试硬编码——`surfaces.test.ts` 和 `status-card.test.ts` 是 deepEqual，**数值改了就得同步改测试**）。

### 4. 跑门禁

```powershell
cd frontend
pnpm test            # 197/197 必须全绿
pnpm typecheck       # tsc --noEmit
pnpm build           # next build --webpack，必须无 error
```

**不要跑 `pnpm e2e`** —— 它是 Playwright，需要 `playwright install chromium` 和系统库 sudo 安装，是分支级而非提交级 gate（见 `CLAUDE.md` "E2E gate (A4)"）。

### 5. 还原 next-env.d.ts 后 push

```powershell
git checkout -- frontend/next-env.d.ts   # 把 .next/dev/types 还原
git status                                # 确认只剩两个 untracked 目录
git push origin feat/multilingual-bge-m3-backend
```

如果用户对动效没意见、不需要微调，**直接执行 1 → 4 → 5**，跳过 3。

---

## 项目锁定项（taste 不可超越）

这些是 brand / 测试 / 合规层面的硬约束，**不可改**：

| 项 | 值 | 锁定来源 |
|---|---|---|
| 主色 | 青黛绿 `#0d9488 ~ #14b8a6` | `CLAUDE.md` 视觉 token 节 |
| 字体 | `Noto Sans SC` | 同上 |
| 页面 padding | `clamp(20px, 4vw, 48px)`（非 shell 内 padding `clamp(12px, 2vw, 24px)`）| 同上 |
| 免责声明字符串 | `非诊断结论、需结合临床。` byte-identical | tests + 合规要求 |
| 整体风格 | 深色 dashboard + 毛玻璃 | 当前已落地、用户认可 |

**特别提醒 GPT**：如果你装了 `frontend-design` 或 `design-taste-frontend` 之类的"创意"skill，**不要触发**它的"挑一个 BOLD aesthetic direction"步骤。本项目品牌 token 已锁。在锁定 palette 内做"微调"，不是"重做"。

---

## 测试断言地图（改 CSS 前先看一眼）

这些测试是回归 trap，改值前查清楚：

| 测试 | 断言对象 | 改 CSS 会触发的失败模式 |
|---|---|---|
| [tests/surfaces.test.ts](../../frontend/tests/surfaces.test.ts) | `getSurfaceCardStyle()` / `getSurfaceSectionStyle()` 的 deepEqual | 改 `lib/ui/surfaces.ts` 任何数值 → 同步改测试 |
| [tests/status-card.test.ts](../../frontend/tests/status-card.test.ts) | `getStatusCardStyle()` 五档 + `getStatusMessageStyle()` 的 deepEqual | 改 `lib/ui/status-card.ts` 任何数值 → 同步改测试 |
| [tests/page-shell-consistency.test.ts](../../frontend/tests/page-shell-consistency.test.ts) | 用正则在 `app/workbench.css` 源文里抓字符串（`meteorFall` / `qiyanStarDrift` / `--qiyan-glass-bg` 等）| 改 CSS 名字 / 删类 → 测试断 |
| `tests/client-section-consistency.test.ts`、`tests/pdf-upload-status.test.ts`、`tests/literature-detail-meta.test.ts` | 各页面源文里的可见文案/结构 | 不应被本次改动触发，但作为保险 |

跑测试时如果失败，先读断言 → 决定"是测试该跟进数值，还是改动越界了"。**不要为了让测试过就放任改动越界。**

---

## 项目大背景（让 GPT 不要做错方向）

- **Qiyan Nexus**：面向 AD（特应性皮炎）医生 / 科研人员的中医药证据 RAG 工作台，仅 B 端、不替代诊断。
- **当前默认运行路径**：deterministic provider + keyword retrieval + JSON backend。**不要改默认配置**。
- **完整规则**见 `CLAUDE.md`（项目根）和 `~/.claude/CLAUDE.md`（用户全局）。其中四原则：think before code / simplicity first / surgical changes / goal-driven。
- **本次任务范围严格收敛在 UI 视觉收尾**，不碰 RAG、不碰 PDF、不碰 eval、不碰后端。

---

## 失败回退

如果 GPT 把改动搞坏了或者用户不喜欢方向：

```powershell
# 回到 origin 状态，丢弃本地两个 commit
git reset --hard origin/feat/multilingual-bge-m3-backend
```

这会丢失 `24b0d78` + `f878784`。**只在用户明确说"全部推倒重来"时做**。如果只是 `f878784` 想撤，做 `git reset --hard 24b0d78` 保留 shell。

---

## 用户对话语气备忘

- 用户偏好简体中文 + 直接列项
- 用户希望 AI **不藏拙**，看到风险立刻说
- 用户给的 K-原则：四条（think before code / simplicity first / surgical changes / goal-driven）
- 用户允许 WebSearch + 学术域名 WebFetch；其他 fetch 仍逐次 prompt

---

## 完成判据（self-check）

收尾完成当：

- [ ] 用户对流星动效签字"OK"
- [ ] `pnpm test` 全绿（197+ 测试）
- [ ] `pnpm typecheck` 通过
- [ ] `pnpm build` 通过
- [ ] `frontend/next-env.d.ts` 已 checkout 还原
- [ ] `git push origin feat/multilingual-bge-m3-backend` 推送成功
- [ ] `论文产出/` 和 `项目实体/` 仍是 untracked（没被错误 add）

任何一项不达标，**先回报用户**，不要硬 push。
