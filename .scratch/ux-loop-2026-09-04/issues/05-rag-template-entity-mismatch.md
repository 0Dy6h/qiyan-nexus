# 05: RAG 回答模板句在问题实体无命中时仍称「检索到相关证据片段」

状态: 已解决（2026-09-06，用户授权技术遗留由 ZCode 对抗性审查代行拍板）
优先级: P2
发现轮次: 第 1 轮（UI 走查）

## 拍板口径与落地

口径选择「提示『问题实体未在证据中出现』+ 引用降格为邻近证据」，不降 citation、不改检索排序与 eval 断言（预期是调参产物，一字未动）：

- `rag.answer_question` 在实体词存在时计算 `entity_matched`（实体命中候选 → True；零命中回退邻近池 → False；无实体词/离题 → None），经 provider 协议新可选参数 `entity_matched` 传入。
- `DeterministicProvider`/`MockClaudeProvider`：`entity_matched=False` 时改用诚实话术「未检索到与所问实体直接对应的证据片段；以下为按相关度排列的 N 条邻近证据片段，对应性未经证实」，`deterministic retrieval` 标记与免责尾注保留；命中与无引用两条既有路径措辞不变（6 处既有断言不涉改）。
- anthropic/opencode_go 提供方签名接受该参数（真实 LLM 措辞归提示词工程，本期不动）。
- eval 基线复核：`test_run_rag_ad_eval_report_meets_baseline_pass_rate` 通过（模板句不在 eval 断言口径内，must_include 均为领域词）。
- 后端 913→918 全绿（+3 provider 契约测试、+2 CORS 测试），verify-local 77.1s 全过，隔离预览 smoke 14 项全过。
