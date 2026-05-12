# Qiyan Nexus Windows Codex → WSL 同步交接

日期：2026-05-11

## 目标

把 Windows 上由 Codex 推进过的岐研枢仓库状态，同步回 WSL 主工作副本，并在仓库内留下可直接阅读的交接文档，避免 repo 内事实源与 wiki 记录漂移。

## 本轮完成内容

- 对比 Windows 源仓库与 WSL 仓库的最近提交
- 将 Windows 侧新增进度同步到 WSL 仓库
- 回读 WSL 仓库最近提交，确认同步结果已落地
- 确认 WSL 工作树干净，可继续作为主工作副本

## 当前仓库事实

- Windows 源仓库：`/mnt/d/开发/TCM_tech`
- WSL 主工作副本：`/home/dyh2026/projects/Tcm_tech`
- 当前分支：`main`
- 当前最新提交：`379551b fix: stabilize frontend build under next 16`

WSL 仓库最近三条提交：
1. `379551b fix: stabilize frontend build under next 16`
2. `e8dd28e [verified] feat: sync windows codex progress into wsl qiyan nexus`
3. `53cea74 feat: add PDF upload storage and mock parse flow for literature detail`

## 这次同步意味着什么

- Windows 上的 PDF upload + mock parse 相关推进，已经进入 WSL 历史链路
- WSL 上已有的前端构建稳定性修复仍然保留在更靠前的提交中
- 后续继续开发时，应默认以 `/home/dyh2026/projects/Tcm_tech` 作为唯一主工作副本，避免再次出现 Windows / WSL 双头推进

## 当前验证范围

本轮直接确认了：
- Windows 仓库最新提交可读出为 `53cea74`
- WSL 仓库当前分支为 `main`
- WSL 仓库最近三条提交顺序符合预期
- WSL `git status --short` 为空

本轮没有重新跑完整测试矩阵，所以这里确认的是“历史同步完成”，不是“所有功能重新回归验证完毕”。

## 下一步建议

优先从以下最小切片中选一个继续：
- PDF 解析结果契约 / 文本抽取占位
- `/compliance` 静态说明页
- 文献 / RAG 体验进一步统一

开始下一轮前，建议先读：
- `AGENTS.md`
- `CONTEXT.md`
- 相关 ADR
- 本文档
