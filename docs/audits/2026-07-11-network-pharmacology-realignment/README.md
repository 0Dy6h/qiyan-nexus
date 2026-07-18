# 网络药理学主轴整改工作区

date: 2026-07-11  
status: active  
authority: 本目录记录本次方向整改；产品当前事实仍以代码、测试和 `docs/current-state.md` 为准。

## 整改目标

把 Qiyan Nexus 从“以 RAG 证据问答为主、网络药理学为 mock 附属功能”的产品，重新收敛为：

> 面向特应性皮炎中医药研究的窄领域网络药理学自动化科研辅助平台；文献检索、PDF 证据归档、证据问答和引用导出是研究链路的证据服务层，而不是产品主轴。

## 隔离与权限规则

- `backend/data/literature/`、`backend/data/network/`、`backend/data/evals/` 作为原始/基线证据，只读审计，不因本次方向整改而重写。
- `backend/data/runtime/`、`backend/uploads/`、`.mcp.json`、`components.json` 不纳入提交或科研事实声明。
- 当前工作树中用户已有的 retrieval Track A 修改必须保留，不覆盖、不回退。
- 本次新增派生审计材料只写入本目录；产品实现修改仍遵守仓库分层、TDD 和验证门禁。
- 自动化结果只能证明 artifact consistency；没有真实数据库版本、查询日期、阈值、人工判定和外部复核时，不声明 scientific readiness。

## 受保护资产与失败行为

- 受保护资产：研究协议、研究对象边界、外部数据来源与版本、派生靶点/网络/富集结果、人工判定、导出报告。
- 可信主体：通过 access token 验证后写入 request state 的 reviewer。
- 不可信输入：浏览器提交的研究参数、外部数据库响应、导入文件、legacy ownerless runtime 数据、客户端修改后的导出内容。
- 必须失败关闭：研究协议缺少明确表型、物种、证据策略或查询日期时，不允许把任务标记为可进入正式网络构建；foreign/ownerless 任务返回 404；报告读取不得推进任务状态。

## 文件说明

- `PLAN.md`：按科研依赖顺序排列的整改门禁。
- `STATUS.md`：当前事实、阻塞项和唯一下一检查点。
- `WORKLOG.md`：追加式操作记录。
- `issues.csv`：问题、证据、处置与关闭条件。
- `evidence_manifest.csv`：整改前基线哈希，只初始化一次。
- `evidence_manifest_check.csv`：后续一致性检查结果，可重复生成但不得覆盖基线含义。

