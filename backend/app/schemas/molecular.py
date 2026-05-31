"""MVP-C 分子对接与分子动力学模拟概念对象（仅类型定义）

本模块为未来 MVP-C 阶段预留类型定义，当前不提供实际功能。
这些对象用于分子对接（Molecular Docking）和分子动力学模拟（Molecular Dynamics Simulation），
是网络药理学研究的下游验证环节。

当前状态：仅 schema 定义，无 router、service 或 repository 实现。
"""

from typing import Literal

from pydantic import BaseModel, Field


class Protein(BaseModel):
    """蛋白结构对象（未实现）

    用于分子对接的靶蛋白，通常从 PDB（Protein Data Bank）获取结构。
    """

    id: str = Field(description="蛋白唯一标识符")
    name: str = Field(description="蛋白名称（英文）")
    name_zh: str | None = Field(default=None, description="蛋白名称（中文）")
    pdb_id: str | None = Field(default=None, description="PDB 数据库 ID（如 1N26）")
    uniprot_id: str | None = Field(default=None, description="UniProt 数据库 ID")
    sequence: str | None = Field(default=None, description="氨基酸序列（FASTA 格式）")
    description: str | None = Field(default=None, description="蛋白功能描述")


class Ligand(BaseModel):
    """小分子配体对象（未实现）

    用于分子对接的小分子化合物，通常是中药活性成分。
    """

    id: str = Field(description="配体唯一标识符")
    name: str = Field(description="配体名称（英文）")
    name_zh: str | None = Field(default=None, description="配体名称（中文）")
    smiles: str | None = Field(default=None, description="SMILES 化学结构表示")
    inchi: str | None = Field(default=None, description="InChI 化学结构表示")
    compound_id: str | None = Field(
        default=None, description="关联到 network compound ID（用于跨模块链接）"
    )
    molecular_weight: float | None = Field(default=None, description="分子量（g/mol）")
    formula: str | None = Field(default=None, description="分子式（如 C15H10O5）")


class DockingResult(BaseModel):
    """分子对接结果（未实现）

    记录蛋白-配体对接的结合能、构象等信息。
    """

    protein_id: str = Field(description="蛋白 ID")
    ligand_id: str = Field(description="配体 ID")
    binding_affinity: float = Field(description="结合亲和力（kcal/mol，越负越强）")
    binding_site: str | None = Field(default=None, description="结合位点描述")
    pose_file: str | None = Field(default=None, description="对接构象文件路径（PDB/MOL2）")
    rmsd: float | None = Field(default=None, description="RMSD 值（Å）")
    interaction_residues: list[str] = Field(
        default_factory=list, description="相互作用残基列表（如 ['ARG123', 'TYR456']）"
    )


class MDSimulationConfig(BaseModel):
    """分子动力学模拟配置（未实现）

    定义 MD 模拟的参数设置。
    """

    temperature: float = Field(default=300.0, description="模拟温度（K）")
    pressure: float = Field(default=1.0, description="模拟压力（bar）")
    simulation_time: float = Field(default=100.0, description="模拟时长（ns）")
    timestep: float = Field(default=2.0, description="时间步长（fs）")
    ensemble: Literal["NVT", "NPT", "NVE"] = Field(default="NPT", description="系综类型")
    force_field: str = Field(default="AMBER99SB", description="力场类型")


class MDSimulationResult(BaseModel):
    """分子动力学模拟结果（未实现）

    记录 MD 模拟的轨迹、能量、RMSD 等分析结果。
    """

    trajectory_file: str | None = Field(default=None, description="轨迹文件路径（XTC/DCD）")
    energy_file: str | None = Field(default=None, description="能量文件路径（EDR/LOG）")
    rmsd_avg: float | None = Field(default=None, description="平均 RMSD（Å）")
    rmsf_avg: float | None = Field(default=None, description="平均 RMSF（Å）")
    total_energy: float | None = Field(default=None, description="总能量（kJ/mol）")
    potential_energy: float | None = Field(default=None, description="势能（kJ/mol）")


class SimulationTask(BaseModel):
    """分子对接/MD 模拟任务（未实现）

    用于异步任务管理，类似于 network analysis task。
    """

    task_id: str = Field(description="任务唯一标识符")
    task_type: Literal["docking", "md_simulation"] = Field(description="任务类型")
    protein_id: str = Field(description="蛋白 ID")
    ligand_id: str = Field(description="配体 ID")
    status: Literal["pending", "running", "completed", "failed"] = Field(
        description="任务状态"
    )
    progress: int = Field(default=0, ge=0, le=100, description="任务进度（0-100）")
    created_at: str = Field(description="创建时间（ISO 8601）")
    started_at: str | None = Field(default=None, description="开始时间（ISO 8601）")
    completed_at: str | None = Field(default=None, description="完成时间（ISO 8601）")
    error_message: str | None = Field(default=None, description="错误信息（失败时）")
    docking_result: DockingResult | None = Field(default=None, description="对接结果")
    md_config: MDSimulationConfig | None = Field(default=None, description="MD 模拟配置")
    md_result: MDSimulationResult | None = Field(default=None, description="MD 模拟结果")
