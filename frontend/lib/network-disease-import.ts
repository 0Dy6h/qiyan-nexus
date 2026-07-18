import type {
  NetworkDiseaseTargetImport,
  NetworkDiseaseTargetRecord,
  NetworkResearchProtocol,
} from "./api/network";

const IMPORT_KEYS = new Set([
  "source_profile",
  "disease",
  "phenotype",
  "species",
  "source_database",
  "database_version",
  "source_query_id",
  "source_query_label",
  "source_query_parameters",
  "query_date",
  "retrieved_at",
  "score_name",
  "applied_threshold",
  "threshold_operator",
  "identifier_mapping",
  "identifier_mapping_version",
  "records",
]);

const RECORD_KEYS = new Set([
  "raw_identifier",
  "canonical_symbol",
  "source_record_id",
  "source_score",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertExactKeys(value: Record<string, unknown>, allowed: Set<string>, label: string) {
  const unsupported = Object.keys(value).filter((key) => !allowed.has(key));
  if (unsupported.length > 0) {
    throw new Error(`${label} 包含不支持的字段：${unsupported.join(", ")}`);
  }
}

function requireString(value: Record<string, unknown>, key: string) {
  const field = value[key];
  if (typeof field !== "string" || field.trim() === "") {
    throw new Error(`疾病靶点 artifact 缺少有效字段：${key}`);
  }
  return field;
}

function parseRecord(value: unknown, index: number): NetworkDiseaseTargetRecord {
  if (!isRecord(value)) {
    throw new Error(`疾病靶点 artifact records[${index}] 必须是对象。`);
  }
  assertExactKeys(value, RECORD_KEYS, `records[${index}]`);
  const sourceScore = value.source_score;
  if (typeof sourceScore !== "number" || !Number.isFinite(sourceScore)) {
    throw new Error(`疾病靶点 artifact records[${index}].source_score 必须是数字。`);
  }
  return {
    raw_identifier: requireString(value, "raw_identifier"),
    canonical_symbol: requireString(value, "canonical_symbol"),
    source_record_id: requireString(value, "source_record_id"),
    source_score: sourceScore,
  };
}

function parseQueryParameters(value: unknown) {
  if (!isRecord(value) || Object.keys(value).length === 0) {
    throw new Error("疾病靶点 artifact 缺少结构化 source_query_parameters。 ");
  }
  for (const parameter of Object.values(value)) {
    const validScalar =
      typeof parameter === "string" ||
      typeof parameter === "number" ||
      typeof parameter === "boolean";
    const validStringList =
      Array.isArray(parameter) && parameter.every((item) => typeof item === "string");
    if (!validScalar && !validStringList) {
      throw new Error("疾病靶点 artifact 的 source_query_parameters 包含不支持的值。 ");
    }
  }
  return value as Record<string, string | number | boolean | string[]>;
}

export function parseNetworkDiseaseTargetImportJson(text: string): NetworkDiseaseTargetImport {
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new Error("疾病靶点 artifact 不是有效 JSON。 ");
  }
  if (!isRecord(value)) {
    throw new Error("疾病靶点 artifact 必须是 JSON 对象。 ");
  }
  assertExactKeys(value, IMPORT_KEYS, "疾病靶点 artifact");
  if (!Array.isArray(value.records)) {
    throw new Error("疾病靶点 artifact 的 records 必须是数组。 ");
  }
  const appliedThreshold = value.applied_threshold;
  if (
    typeof appliedThreshold !== "number" ||
    !Number.isFinite(appliedThreshold) ||
    appliedThreshold < 0 ||
    appliedThreshold > 1
  ) {
    throw new Error("疾病靶点 artifact 的 applied_threshold 必须在 0 到 1 之间。 ");
  }

  const imported: NetworkDiseaseTargetImport = {
    source_profile: requireString(value, "source_profile") as "open_targets_association_v1",
    disease: requireString(value, "disease") as "atopic_dermatitis",
    phenotype: requireString(value, "phenotype"),
    species: requireString(value, "species") as "Homo sapiens",
    source_database: requireString(value, "source_database") as "Open Targets Platform",
    database_version: requireString(value, "database_version"),
    source_query_id: requireString(value, "source_query_id"),
    source_query_label: requireString(value, "source_query_label"),
    source_query_parameters: parseQueryParameters(value.source_query_parameters),
    query_date: requireString(value, "query_date"),
    retrieved_at: requireString(value, "retrieved_at"),
    score_name: requireString(value, "score_name") as "association_score",
    applied_threshold: appliedThreshold,
    threshold_operator: requireString(value, "threshold_operator") as "gte",
    identifier_mapping: requireString(
      value,
      "identifier_mapping",
    ) as "Ensembl target approvedSymbol",
    identifier_mapping_version: requireString(value, "identifier_mapping_version"),
    records: value.records.map(parseRecord),
  };

  if (
    imported.source_profile !== "open_targets_association_v1" ||
    imported.disease !== "atopic_dermatitis" ||
    imported.species !== "Homo sapiens" ||
    imported.source_database !== "Open Targets Platform" ||
    imported.score_name !== "association_score" ||
    imported.threshold_operator !== "gte" ||
    imported.identifier_mapping !== "Ensembl target approvedSymbol"
  ) {
    throw new Error("疾病靶点 artifact 不符合 Open Targets association v1 profile。 ");
  }
  return imported;
}

export function getDiseaseImportProtocolMismatch(
  imported: NetworkDiseaseTargetImport,
  protocol: NetworkResearchProtocol,
) {
  for (const field of ["disease", "phenotype", "species", "query_date"] as const) {
    if (imported[field] !== protocol[field]) {
      return `疾病靶点 artifact 的 ${field} 与当前研究协议不一致。`;
    }
  }
  return null;
}
