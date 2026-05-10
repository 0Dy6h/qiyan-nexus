"use client";

import { FormEvent, useMemo, useState } from "react";

import {
  buildPdfDownloadUrl,
  getParseAttemptLabel,
  getParseTriggerLabel,
  LiteratureItem,
  PdfUploadResponse,
  runFakePdfAutoParse,
  updatePdfParseStatus,
  uploadLiteraturePdf,
} from "../lib/api/literature";
import { getPdfActionLabels, getPdfStatusCopy, getPdfStatusTone } from "../lib/ui/status-card";
import { CardMetaRow } from "./CardMeta";
import StatusPanel from "./StatusPanel";

type LiteraturePdfUploadClientProps = {
  item: LiteratureItem;
};

type UploadState = {
  fileName: string;
  result: PdfUploadResponse | null;
  currentItem: LiteratureItem;
  error: string | null;
  isLoading: boolean;
  isParsing: boolean;
  isUpdatingStatus: boolean;
};

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return null;
  }
  return value;
}

export default function LiteraturePdfUploadClient({ item }: LiteraturePdfUploadClientProps) {
  const [state, setState] = useState<UploadState>({
    fileName: item.pdf_file_name ?? "",
    result: null,
    currentItem: item,
    error: null,
    isLoading: false,
    isParsing: false,
    isUpdatingStatus: false,
  });

  const currentStatus = state.result?.pdf_parse_status ?? state.currentItem.pdf_parse_status;
  const currentUploadId = state.result?.pdf_upload_id ?? state.currentItem.pdf_upload_id;
  const currentFileName = state.result?.file_name ?? state.currentItem.pdf_file_name;
  const currentStoragePath = state.result?.storage_path ?? null;
  const currentParseMessage = state.currentItem.pdf_parse_message ?? null;
  const currentParseStartedAt = state.currentItem.pdf_parse_started_at ?? null;
  const currentParseFinishedAt = state.currentItem.pdf_parse_finished_at ?? null;
  const currentParseTrigger = getParseTriggerLabel(state.currentItem.last_parse_trigger ?? null);
  const currentParseAttempt = getParseAttemptLabel(state.currentItem.parse_attempt_count ?? null);
  const currentPdfDownloadUrl = currentUploadId ? buildPdfDownloadUrl(currentUploadId) : null;
  const statusTone = useMemo(() => getPdfStatusTone(currentStatus), [currentStatus]);
  const actionLabels = useMemo(() => getPdfActionLabels(currentStatus), [currentStatus]);
  const statusCopy = useMemo(
    () => getPdfStatusCopy(currentStatus, state.isParsing, currentParseMessage),
    [currentStatus, state.isParsing, currentParseMessage],
  );

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");

    if (!(file instanceof File) || !file.name) {
      setState((current) => ({ ...current, error: "请选择要上传的 PDF 文件。", result: null }));
      return;
    }

    setState((current) => ({ ...current, fileName: file.name, result: null, error: null, isLoading: true, isParsing: false }));

    try {
      const result = await uploadLiteraturePdf(state.currentItem.id, file);
      setState((current) => ({
        ...current,
        fileName: result.file_name,
        result,
        currentItem: {
          ...current.currentItem,
          pdf_upload_id: result.pdf_upload_id,
          pdf_file_name: result.file_name,
          pdf_parse_status: result.pdf_parse_status,
          pdf_parse_message: null,
          pdf_parse_started_at: null,
          pdf_parse_finished_at: null,
          last_parse_trigger: null,
          parse_attempt_count: 0,
        },
        error: null,
        isLoading: false,
        isParsing: true,
      }));

      const parsedItem = await runFakePdfAutoParse(state.currentItem.id, result.file_name);
      setState((current) => ({
        ...current,
        currentItem: parsedItem,
        result: current.result
          ? {
              ...current.result,
              pdf_parse_status: parsedItem.pdf_parse_status ?? current.result.pdf_parse_status,
            }
          : current.result,
        error: null,
        isParsing: false,
      }));
    } catch {
      setState((current) => ({
        ...current,
        fileName: file.name,
        result: current.result,
        error: current.isLoading ? "PDF 上传失败，请稍后重试。" : "PDF 自动解析失败，请稍后重试。",
        isLoading: false,
        isParsing: false,
      }));
    }
  }

  async function onUpdateStatus(nextStatus: "parsed" | "failed") {
    setState((current) => ({ ...current, error: null, isUpdatingStatus: true }));

    try {
      const updatedItem = await updatePdfParseStatus(state.currentItem.id, nextStatus);
      setState((current) => ({
        ...current,
        currentItem: updatedItem,
        result: current.result
          ? {
              ...current.result,
              pdf_parse_status: updatedItem.pdf_parse_status ?? current.result.pdf_parse_status,
            }
          : current.result,
        error: null,
        isUpdatingStatus: false,
      }));
    } catch {
      setState((current) => ({
        ...current,
        error: "PDF 解析状态更新失败，请稍后重试。",
        isUpdatingStatus: false,
      }));
    }
  }

  return (
    <section
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: 16,
        padding: 24,
        display: "grid",
        gap: 16,
      }}
    >
      <div style={{ display: "grid", gap: 8 }}>
        <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>PDF 上传与解析状态</h2>
        <p style={{ color: "#64748b", margin: 0 }}>
          上传 PDF 后，当前文献会先写入 `pdf_upload_id` 与 `pending`，随后前端显式触发 mock 解析步骤。
        </p>
      </div>

      <StatusPanel message={statusCopy} tone={statusTone} />

      <CardMetaRow
        items={[
          currentUploadId ? `Upload ID ${currentUploadId}` : null,
          currentFileName ? `文件 ${currentFileName}` : null,
          currentStoragePath ? `存储 ${currentStoragePath}` : null,
        ]}
      />

      {currentPdfDownloadUrl ? (
        <a
          href={currentPdfDownloadUrl}
          target="_blank"
          rel="noreferrer"
          style={{ color: "#0d9488", fontWeight: 700, width: "fit-content" }}
        >
          预览 PDF
        </a>
      ) : null}

      <CardMetaRow
        items={[
          currentParseTrigger ? `触发 ${currentParseTrigger}` : null,
          currentParseAttempt ? currentParseAttempt : null,
          currentParseStartedAt ? `开始 ${formatTimestamp(currentParseStartedAt)}` : null,
          currentParseFinishedAt ? `结束 ${formatTimestamp(currentParseFinishedAt)}` : null,
        ]}
      />

      <form onSubmit={onSubmit} style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <input
          name="file"
          type="file"
          accept="application/pdf,.pdf"
          aria-label="上传 PDF"
          style={{ color: "#334155" }}
        />
        <button
          type="submit"
          disabled={state.isLoading || state.isParsing || state.isUpdatingStatus}
          style={{
            border: 0,
            borderRadius: 8,
            background: state.isLoading || state.isParsing ? "#94a3b8" : "#0d9488",
            color: "white",
            fontSize: 15,
            fontWeight: 700,
            padding: "10px 16px",
          }}
        >
          {state.isLoading ? "上传中..." : state.isParsing ? "解析中..." : "上传 PDF"}
        </button>
        {state.fileName ? <span style={{ color: "#64748b" }}>当前选择：{state.fileName}</span> : null}
      </form>

      {actionLabels.length > 0 ? (
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            type="button"
            disabled={state.isUpdatingStatus || state.isLoading || state.isParsing}
            onClick={() => onUpdateStatus("parsed")}
            style={{
              border: 0,
              borderRadius: 8,
              background: state.isUpdatingStatus ? "#94a3b8" : "#16a34a",
              color: "white",
              fontSize: 15,
              fontWeight: 700,
              padding: "10px 16px",
            }}
          >
            {state.isUpdatingStatus ? "状态更新中..." : actionLabels[0]}
          </button>
          <button
            type="button"
            disabled={state.isUpdatingStatus || state.isLoading || state.isParsing}
            onClick={() => onUpdateStatus("failed")}
            style={{
              border: 0,
              borderRadius: 8,
              background: state.isUpdatingStatus ? "#94a3b8" : "#dc2626",
              color: "white",
              fontSize: 15,
              fontWeight: 700,
              padding: "10px 16px",
            }}
          >
            {state.isUpdatingStatus ? "状态更新中..." : actionLabels[1]}
          </button>
        </div>
      ) : null}

      {state.error ? <StatusPanel message={state.error} tone="error" /> : null}
    </section>
  );
}
