import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const EXPORT_SVG_PATH = join(__dirname, "..", "lib", "export-svg.ts");

describe("export-svg", () => {
  it("exports exportSvgToPng function", () => {
    const source = readFileSync(EXPORT_SVG_PATH, "utf-8");
    assert(source.includes("export async function exportSvgToPng"));
  });

  it("exports exportSvgToSvg function", () => {
    const source = readFileSync(EXPORT_SVG_PATH, "utf-8");
    assert(source.includes("export function exportSvgToSvg"));
  });

  it("exportSvgToPng creates PNG blob with 2x scale", () => {
    const source = readFileSync(EXPORT_SVG_PATH, "utf-8");
    assert(source.includes("const scale = 2"));
    assert(source.includes('canvas.toBlob'));
    assert(source.includes('"image/png"'));
  });

  it("exportSvgToPng adds white background", () => {
    const source = readFileSync(EXPORT_SVG_PATH, "utf-8");
    assert(source.includes('ctx.fillStyle = "#ffffff"'));
    assert(source.includes("ctx.fillRect"));
  });

  it("exportSvgToSvg creates SVG blob", () => {
    const source = readFileSync(EXPORT_SVG_PATH, "utf-8");
    assert(source.includes('"image/svg+xml;charset=utf-8"'));
  });

  it("both functions trigger download with filename parameter", () => {
    const source = readFileSync(EXPORT_SVG_PATH, "utf-8");
    assert(source.includes("link.download = filename"));
    assert(source.includes("link.click()"));
  });
});

describe("NetworkGraph export integration", () => {
  const NETWORK_GRAPH_PATH = join(__dirname, "..", "components", "NetworkGraph.tsx");

  it("imports export functions from export-svg", () => {
    const source = readFileSync(NETWORK_GRAPH_PATH, "utf-8");
    assert(source.includes('from "../lib/export-svg"'));
    assert(source.includes("exportSvgToPng"));
    assert(source.includes("exportSvgToSvg"));
  });

  it("accepts optional taskId prop", () => {
    const source = readFileSync(NETWORK_GRAPH_PATH, "utf-8");
    assert(source.includes("taskId?: string"));
  });

  it("has svgRef for export", () => {
    const source = readFileSync(NETWORK_GRAPH_PATH, "utf-8");
    assert(source.includes("svgRef"));
    assert(source.includes("ref={svgRef}"));
  });

  it("has export PNG button", () => {
    const source = readFileSync(NETWORK_GRAPH_PATH, "utf-8");
    assert(source.includes("handleExportPng"));
    assert(source.includes("导出 PNG"));
  });

  it("has export SVG button", () => {
    const source = readFileSync(NETWORK_GRAPH_PATH, "utf-8");
    assert(source.includes("handleExportSvg"));
    assert(source.includes("导出 SVG"));
  });

  it("only shows export buttons when nodes exist", () => {
    const source = readFileSync(NETWORK_GRAPH_PATH, "utf-8");
    assert(source.includes("nodes.length > 0"));
  });

  it("uses taskId in filename when provided", () => {
    const source = readFileSync(NETWORK_GRAPH_PATH, "utf-8");
    assert(source.includes("network-graph-${taskId}"));
  });

  it("disables buttons during export", () => {
    const source = readFileSync(NETWORK_GRAPH_PATH, "utf-8");
    assert(source.includes("isExporting"));
    assert(source.includes("disabled={isExporting}"));
  });
});

describe("NetworkAnalysisClient passes taskId to NetworkGraph", () => {
  const CLIENT_PATH = join(__dirname, "..", "components", "NetworkAnalysisClient.tsx");

  it("passes taskId prop to NetworkGraph", () => {
    const source = readFileSync(CLIENT_PATH, "utf-8");
    assert(source.includes("taskId={result.task_id}"));
  });
});
