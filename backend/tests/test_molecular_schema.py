"""Tests for MVP-C molecular schema definitions (placeholder only)."""

from app.schemas.molecular import (
    DockingResult,
    Ligand,
    MDSimulationConfig,
    MDSimulationResult,
    Protein,
    SimulationTask,
)


def test_protein_schema_validates():
    """Protein schema accepts valid fields."""
    protein = Protein(
        id="P001",
        name="IL6 Receptor",
        name_zh="白细胞介素-6 受体",
        pdb_id="1N26",
        uniprot_id="P08887",
        sequence="MKLVLLVTSLLLCELPHPAFLLIP...",
        description="Interleukin-6 receptor subunit alpha",
    )
    assert protein.id == "P001"
    assert protein.name == "IL6 Receptor"
    assert protein.pdb_id == "1N26"


def test_protein_optional_fields():
    """Protein schema allows None for optional fields."""
    protein = Protein(id="P002", name="TNF Receptor")
    assert protein.name_zh is None
    assert protein.pdb_id is None
    assert protein.sequence is None


def test_ligand_schema_validates():
    """Ligand schema accepts valid fields."""
    ligand = Ligand(
        id="L001",
        name="Quercetin",
        name_zh="槲皮素",
        smiles="C1=CC(=C(C=C1C2=C(C(=O)C3=C(C=C(C=C3O2)O)O)O)O)O",
        compound_id="compound-quercetin",
        molecular_weight=302.24,
        formula="C15H10O7",
    )
    assert ligand.id == "L001"
    assert ligand.name == "Quercetin"
    assert ligand.molecular_weight == 302.24


def test_docking_result_schema_validates():
    """DockingResult schema accepts valid fields."""
    result = DockingResult(
        protein_id="P001",
        ligand_id="L001",
        binding_affinity=-8.5,
        binding_site="Active site pocket",
        rmsd=1.2,
        interaction_residues=["ARG123", "TYR456", "ASP789"],
    )
    assert result.binding_affinity == -8.5
    assert len(result.interaction_residues) == 3


def test_md_simulation_config_schema_validates():
    """MDSimulationConfig schema accepts valid fields."""
    config = MDSimulationConfig(
        temperature=310.0,
        pressure=1.0,
        simulation_time=200.0,
        timestep=2.0,
        ensemble="NPT",
        force_field="CHARMM36",
    )
    assert config.temperature == 310.0
    assert config.ensemble == "NPT"


def test_md_simulation_config_defaults():
    """MDSimulationConfig uses default values."""
    config = MDSimulationConfig()
    assert config.temperature == 300.0
    assert config.pressure == 1.0
    assert config.simulation_time == 100.0
    assert config.ensemble == "NPT"


def test_md_simulation_result_schema_validates():
    """MDSimulationResult schema accepts valid fields."""
    result = MDSimulationResult(
        trajectory_file="/path/to/trajectory.xtc",
        energy_file="/path/to/energy.edr",
        rmsd_avg=2.5,
        rmsf_avg=1.8,
        total_energy=-125000.0,
        potential_energy=-150000.0,
    )
    assert result.rmsd_avg == 2.5
    assert result.total_energy == -125000.0


def test_simulation_task_schema_validates():
    """SimulationTask schema accepts valid fields."""
    task = SimulationTask(
        task_id="sim-001",
        task_type="docking",
        protein_id="P001",
        ligand_id="L001",
        status="pending",
        progress=0,
        created_at="2026-06-01T10:00:00Z",
    )
    assert task.task_id == "sim-001"
    assert task.task_type == "docking"
    assert task.status == "pending"


def test_simulation_task_with_docking_result():
    """SimulationTask can include docking result."""
    docking_result = DockingResult(
        protein_id="P001",
        ligand_id="L001",
        binding_affinity=-7.2,
    )
    task = SimulationTask(
        task_id="sim-002",
        task_type="docking",
        protein_id="P001",
        ligand_id="L001",
        status="completed",
        progress=100,
        created_at="2026-06-01T10:00:00Z",
        completed_at="2026-06-01T10:05:00Z",
        docking_result=docking_result,
    )
    assert task.status == "completed"
    assert task.docking_result is not None
    assert task.docking_result.binding_affinity == -7.2


def test_simulation_task_with_md_result():
    """SimulationTask can include MD simulation result."""
    md_config = MDSimulationConfig(simulation_time=50.0)
    md_result = MDSimulationResult(rmsd_avg=3.0)
    task = SimulationTask(
        task_id="sim-003",
        task_type="md_simulation",
        protein_id="P001",
        ligand_id="L001",
        status="completed",
        progress=100,
        created_at="2026-06-01T10:00:00Z",
        completed_at="2026-06-01T11:00:00Z",
        md_config=md_config,
        md_result=md_result,
    )
    assert task.task_type == "md_simulation"
    assert task.md_config is not None
    assert task.md_result is not None
    assert task.md_result.rmsd_avg == 3.0


def test_simulation_task_progress_constraints():
    """SimulationTask progress is constrained to 0-100."""
    task = SimulationTask(
        task_id="sim-004",
        task_type="docking",
        protein_id="P001",
        ligand_id="L001",
        status="running",
        progress=50,
        created_at="2026-06-01T10:00:00Z",
    )
    assert 0 <= task.progress <= 100
