# C6 MVP-C Schema Placeholder Handoff

**日期**: 2026-06-01  
**状态**: 已完成  
**任务**: 为 MVP-C 分子对接/MD 模拟预留类型定义

---

## 目标

为未来 MVP-C 阶段（分子对接与分子动力学模拟）预留 Pydantic schema 定义，确保与现有 network 模块的数据模型一致性，但**当前不实现任何业务逻辑**。

## 已完成的工作

### 1. Schema 定义

**新增文件**：`backend/app/schemas/molecular.py`

**定义的对象**：

#### Protein（蛋白结构对象）
- `id` - 蛋白唯一标识符
- `name` / `name_zh` - 蛋白名称（英文/中文）
- `pdb_id` - PDB 数据库 ID（如 1N26）
- `uniprot_id` - UniProt 数据库 ID
- `sequence` - 氨基酸序列（FASTA 格式）
- `description` - 蛋白功能描述

#### Ligand（小分子配体对象）
- `id` - 配体唯一标识符
- `name` / `name_zh` - 配体名称（英文/中文）
- `smiles` - SMILES 化学结构表示
- `inchi` - InChI 化学结构表示
- `compound_id` - 关联到 network compound ID（跨模块链接）
- `molecular_weight` - 分子量（g/mol）
- `formula` - 分子式（如 C15H10O5）

#### DockingResult（分子对接结果）
- `protein_id` / `ligand_id` - 蛋白和配体 ID
- `binding_affinity` - 结合亲和力（kcal/mol，越负越强）
- `binding_site` - 结合位点描述
- `pose_file` - 对接构象文件路径（PDB/MOL2）
- `rmsd` - RMSD 值（Å）
- `interaction_residues` - 相互作用残基列表

#### MDSimulationConfig（MD 模拟配置）
- `temperature` - 模拟温度（K，默认 300.0）
- `pressure` - 模拟压力（bar，默认 1.0）
- `simulation_time` - 模拟时长（ns，默认 100.0）
- `timestep` - 时间步长（fs，默认 2.0）
- `ensemble` - 系综类型（NVT/NPT/NVE，默认 NPT）
- `force_field` - 力场类型（默认 AMBER99SB）

#### MDSimulationResult（MD 模拟结果）
- `trajectory_file` - 轨迹文件路径（XTC/DCD）
- `energy_file` - 能量文件路径（EDR/LOG）
- `rmsd_avg` / `rmsf_avg` - 平均 RMSD/RMSF（Å）
- `total_energy` / `potential_energy` - 总能量/势能（kJ/mol）

#### SimulationTask（对接/MD 模拟任务）
- `task_id` - 任务唯一标识符
- `task_type` - 任务类型（docking / md_simulation）
- `protein_id` / `ligand_id` - 蛋白和配体 ID
- `status` - 任务状态（pending / running / completed / failed）
- `progress` - 任务进度（0-100）
- `created_at` / `started_at` / `completed_at` - 时间戳
- `error_message` - 错误信息（失败时）
- `docking_result` - 对接结果（可选）
- `md_config` / `md_result` - MD 配置和结果（可选）

### 2. 测试覆盖

**新增测试**：`backend/tests/test_molecular_schema.py`（11 个测试）

**测试内容**：
- `test_protein_schema_validates` - Protein schema 验证
- `test_protein_optional_fields` - 可选字段验证
- `test_ligand_schema_validates` - Ligand schema 验证
- `test_docking_result_schema_validates` - DockingResult schema 验证
- `test_md_simulation_config_schema_validates` - MDSimulationConfig 验证
- `test_md_simulation_config_defaults` - 默认值验证
- `test_md_simulation_result_schema_validates` - MDSimulationResult 验证
- `test_simulation_task_schema_validates` - SimulationTask 验证
- `test_simulation_task_with_docking_result` - 包含对接结果的任务
- `test_simulation_task_with_md_result` - 包含 MD 结果的任务
- `test_simulation_task_progress_constraints` - 进度约束验证

**测试结果**：
- 后端：304 个测试通过（从 293 增加到 304）
- 前端：137 个测试通过（无变化）

### 3. 文档更新

**README.md**：
- 添加"MVP-C 概念对象（仅 schema 预留）"章节
- 列出已定义的 schema
- 明确当前状态：✅ Schema 定义、✅ 测试覆盖、❌ 无实现、❌ 不应使用

**docs/adr/0010-research-workbench-module-roadmap.md**：
- 添加"实施状态"章节
- 标记 MVP-C schema 已预留（2026-06-01）
- 明确下一步：等待 MVP-B 稳定后再推进实际功能

---

## 设计考虑

### 1. 与 Network 模块的一致性

- `Ligand.compound_id` 字段用于关联 network 模块的 compound 对象
- 任务模型（`SimulationTask`）与 `NetworkTaskRecord` 保持相似结构
- 状态枚举（pending/running/completed/failed）与 network 任务一致

### 2. 科研领域标准

- **PDB**：Protein Data Bank，蛋白结构数据库
- **UniProt**：蛋白序列和功能注释数据库
- **SMILES/InChI**：化学结构表示标准
- **RMSD/RMSF**：分子动力学常用指标
- **力场**：AMBER、CHARMM、GROMOS 等分子模拟力场

### 3. 异步任务模式

- `SimulationTask` 设计为异步任务，类似 `NetworkTaskRecord`
- 支持进度跟踪（0-100）
- 支持错误处理（error_message）
- 支持时间戳记录（created_at / started_at / completed_at）

---

## 当前状态

### ✅ 已完成
- Pydantic schema 定义（6 个对象）
- 完整的字段文档（Field description）
- 11 个 schema 验证测试
- README 和 ADR 文档更新

### ❌ 未实现（故意不实现）
- 无 API router（`/api/molecular/*`）
- 无 service 层（`app/services/molecular.py`）
- 无 repository 层（`app/repositories/molecular.py`）
- 无前端页面（`/molecular`）
- 无前端类型定义（`frontend/lib/api/molecular.ts`）
- 无实际的分子对接或 MD 模拟功能

### ⚠️ 重要提示

**这些对象当前不应在代码中使用**。它们仅作为类型定义预留，为未来 MVP-C 阶段提供参考。

---

## 后续实施路径（MVP-C 阶段）

当 MVP-B（网络药理学）稳定后，可按以下顺序推进 MVP-C：

### 阶段 1：分子对接基础（估计 2 周）
1. 实现 Protein/Ligand repository（本地 JSON 或数据库）
2. 实现 DockingTask service（异步任务管理）
3. 集成 AutoDock Vina 或 Smina（Docker 容器）
4. 实现 `/api/molecular/docking` API
5. 前端页面：提交对接任务、查看结果

### 阶段 2：对接结果可视化（估计 1 周）
1. 集成 3Dmol.js 或 NGL Viewer
2. 展示蛋白-配体复合物结构
3. 高亮结合位点和相互作用残基
4. 导出对接报告（Markdown/PDF）

### 阶段 3：分子动力学模拟（估计 3 周）
1. 集成 GROMACS 或 OpenMM（Docker 容器）
2. 实现 MDSimulationTask service
3. 实现 `/api/molecular/md` API
4. 轨迹分析：RMSD、RMSF、Rg、SASA、氢键
5. 前端页面：提交 MD 任务、查看轨迹和分析结果

### 阶段 4：与 Network 模块集成（估计 1 周）
1. 从 network 富集分析结果推荐对接候选
2. 一键提交"成分-靶点"对接任务
3. 对接结果反馈到 network 分析报告

---

## 验证步骤

### 自动化测试

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest tests/test_molecular_schema.py -v
& .\.uv-test-venv\Scripts\python.exe -m pytest -q  # 全部测试
```

### 验证 Schema 不被使用

```bash
# 确认 molecular.py 不被任何 router 导入
grep -r "from app.schemas.molecular" backend/app/api/
# 应该返回空（无匹配）

# 确认 molecular.py 不被任何 service 导入
grep -r "from app.schemas.molecular" backend/app/services/
# 应该返回空（无匹配）
```

---

## 关键文件

### 后端
- `backend/app/schemas/molecular.py` - MVP-C schema 定义（新建）
- `backend/tests/test_molecular_schema.py` - Schema 测试（新建）

### 文档
- `README.md` - 添加 MVP-C 概念对象说明
- `docs/adr/0010-research-workbench-module-roadmap.md` - 更新实施状态
- `docs/handoffs/2026-06-01-c6-mvp-c-schema-placeholder.md` - 本文档

---

## 推荐阅读顺序

1. 本 handoff
2. `backend/app/schemas/molecular.py` - 查看 schema 定义和文档
3. `backend/tests/test_molecular_schema.py` - 查看测试用例
4. `docs/adr/0010-research-workbench-module-roadmap.md` - 理解模块路线图

---

## 总结

C6 任务已完成，MVP-C 的类型定义已预留。这些 schema 为未来的分子对接和 MD 模拟功能提供了清晰的数据模型参考，同时确保不会干扰当前的开发工作。

**下一步**：C4-C6 全部完成，可以合并到 main 并推送到远程仓库。
