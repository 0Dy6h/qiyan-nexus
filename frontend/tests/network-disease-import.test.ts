import assert from "node:assert/strict";
import { test } from "node:test";

import {
  getDiseaseImportProtocolMismatch,
  parseNetworkDiseaseTargetImportJson,
} from "../lib/network-disease-import";

const VALID_IMPORT = {
  source_profile: "open_targets_association_v1",
  disease: "atopic_dermatitis",
  phenotype: "特应性皮炎伴 2 型炎症与皮肤屏障异常",
  species: "Homo sapiens",
  source_database: "Open Targets Platform",
  database_version: "25.06",
  source_query_id: "EFO_0000274",
  source_query_label: "atopic eczema",
  source_query_parameters: { datatypes: ["genetic_association"] },
  query_date: "2026-07-11",
  retrieved_at: "2026-07-11T08:30:00Z",
  score_name: "association_score",
  applied_threshold: 0.6,
  threshold_operator: "gte",
  identifier_mapping: "Ensembl target approvedSymbol",
  identifier_mapping_version: "25.06",
  records: [],
};

test("parseNetworkDiseaseTargetImportJson accepts a frozen zero-hit import", () => {
  const parsed = parseNetworkDiseaseTargetImportJson(JSON.stringify(VALID_IMPORT));

  assert.equal(parsed.source_profile, "open_targets_association_v1");
  assert.equal(parsed.database_version, "25.06");
  assert.deepEqual(parsed.records, []);
});

test("parseNetworkDiseaseTargetImportJson rejects server-only provenance fields", () => {
  assert.throws(
    () =>
      parseNetworkDiseaseTargetImportJson(
        JSON.stringify({
          ...VALID_IMPORT,
          provenance_verification_status: "verified",
        }),
      ),
    /不支持的字段/,
  );
});

test("getDiseaseImportProtocolMismatch reports immutable protocol drift", () => {
  const imported = parseNetworkDiseaseTargetImportJson(JSON.stringify(VALID_IMPORT));

  assert.equal(
    getDiseaseImportProtocolMismatch(imported, {
      disease: "atopic_dermatitis",
      phenotype: "特应性皮炎伴瘙痒",
      species: "Homo sapiens",
      evidence_policy: "direct_human_first",
      query_date: "2026-07-11",
    }),
    "疾病靶点 artifact 的 phenotype 与当前研究协议不一致。",
  );
});
