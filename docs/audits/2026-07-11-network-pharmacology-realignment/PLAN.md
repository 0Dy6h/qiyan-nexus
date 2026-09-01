# 整改计划

## Gate 0 — 产品契约

- 明确唯一主轴：网络药理学科研项目工作流。
- 明确证据服务层：文献检索、PDF、RAG、导出只为研究问题、靶点边和结论提供证据。
- 明确默认模式：可以离线/mock 演练，但 UI、API 和报告必须呈现与正式研究相同的协议字段和门禁。

完成定义：入口、导航、事实源和 API 契约不再把 RAG 描述为第一主流程。

## Gate 1 — 研究协议与前置门禁

- 观察单元：方剂或单味中药。
- 疾病范围：特应性皮炎。
- 必填表型：不得只写宽泛 disease target union。
- 必填物种：当前只接受 human。
- 必填证据策略：区分直接人类疾病证据、文献支持、预测关联与 mock。
- 必填查询日期；未来真实模式还需数据库版本、阈值和标识符映射记录。

完成定义：未满足协议的任务在 API 层 422；合法协议完整持久化并进入报告。

## Gate 2 — 数据来源与靶点集合

状态：**partial foundation**。集合分离、严格 disease import snapshot、稳定 source-row IDs、双侧 intersection refs、人工判定空状态与独立 artifact validator 已落地；疾病来源仍是未验证客户端导入，compound 真实版本/阈值和人工 adjudication 尚未完成，因此不得标为 closed。

- 每个来源记录数据库、版本/日期、物种、score/threshold、标识符映射。
- 疾病靶点、成分靶点和交集集合分别输出，禁止用宽泛 union 冒充表型特异集合。
- disease import 在 task 创建时封存；客户端不得声明 server provenance、row ID、intersection 或人工判定字段。
- intersection 每个 canonical symbol 一条派生 row，并完整引用 disease/compound 两侧匹配 lineage IDs。
- 生成逐行 lineage 表，允许人工排除与理由记录。

完成定义：任何靶点可追溯到来源记录与转换规则。

## Gate 3 — 网络与富集

- 预注册 core selection 规则，再计算 PPI 排名。
- 富集报告背景集、输入基因、校正方法、完整 top terms。
- CSV、图、表和报告从同一派生对象生成并交叉校验。

完成定义：artifact consistency 独立复算通过；scientific readiness 单独标记。

## Gate 4 — 证据服务闭环

- 文献检索可绑定研究项目、靶点、通路或边。
- RAG 只能基于项目证据包回答，并输出 claim-to-source 映射。
- 导出包含研究协议、来源范围、限制、人工判定状态和免责声明。

完成定义：证据服务不再是平行产品，而是网络研究对象的可追溯支撑层。

## Gate 5 — 真实数据最小闭环

- 只选择一个方剂和一个明确 AD 表型。
- 冻结真实外部来源版本与查询参数。
- 先跑小规模可人工复核链路，再决定是否扩大数据量或引入重基础设施。

完成定义：至少一条 compound-target-pathway 链具备逐边来源、人工复核与保守结论。
