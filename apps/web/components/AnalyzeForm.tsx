"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { AnalyzeRequestSchema, type AnalyzeRequest } from "@/lib/schemas";
import { useAnalyzeMutation, type AnalyzeResponse } from "@/features/analyze/hooks";
import { useUploadMutation, type UploadResponse } from "@/features/analyze/uploadHooks";
import { ApiError } from "@/lib/api";
import { saveRecentAnalysis } from "@/lib/recentAnalyses";
import { proxyPaths } from "@/lib/config";

/* ------------------------------------------------------------------ */
/*  Shared input style                                                */
/* ------------------------------------------------------------------ */

const INPUT_BASE =
  "rounded-lg border px-3.5 py-2.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:ring-2 focus:ring-[#4F46E5]/30";
const INPUT_OK = "border-gray-200 focus:border-[#4F46E5]";
const INPUT_ERR = "border-red-400 focus:border-red-400";

type Mode = "paste" | "upload";

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function AnalyzeForm() {
  const [mode, setMode] = useState<Mode>("paste");

  const [form, setForm] = useState<AnalyzeRequest>({
    title: "",
    subject: "",
    grade_band: "",
    curriculum_text: "",
    rubric_text: "",
  });

  const [fieldErrors, setFieldErrors] = useState<Partial<Record<string, string>>>({});

  // Upload state
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);

  // Preview state
  const [previewText, setPreviewText] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);

  const analyzeMutation = useAnalyzeMutation();
  const uploadMutation = useUploadMutation();

  /* ---- helpers ---- */

  function handleChange(name: keyof AnalyzeRequest, value: string) {
    setForm((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  }

  function switchMode(next: Mode) {
    setMode(next);
    setFieldErrors({});
    // Clear content-source fields when switching
    setForm((prev) => ({ ...prev, curriculum_text: "", document_id: undefined }));
    setUploadResult(null);
    setPreviewText(null);
    setPreviewOpen(false);
    uploadMutation.reset();
  }

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setFieldErrors((prev) => ({ ...prev, file: "Select a file first" }));
      return;
    }
    setFieldErrors((prev) => ({ ...prev, file: undefined }));

    const fd = new FormData();
    fd.append("file", file);
    if (form.title) fd.append("title", form.title);
    if (form.subject) fd.append("subject", form.subject);
    if (form.grade_band) fd.append("grade_band", form.grade_band);

    uploadMutation.mutate(fd, {
      onSuccess: (data) => {
        setUploadResult(data);
        setPreviewText(null);
        setPreviewOpen(false);
        setForm((prev) => ({ ...prev, document_id: data.document_id }));
      },
    });
  }

  async function handlePreview() {
    if (!uploadResult) return;
    if (previewText !== null) {
      setPreviewOpen((prev) => !prev);
      return;
    }
    setPreviewLoading(true);
    try {
      const res = await fetch(proxyPaths.documentPreview(uploadResult.document_id));
      if (!res.ok) throw new Error(`Preview failed (${res.status})`);
      const data = await res.json();
      setPreviewText(data.preview_text ?? "");
      setPreviewOpen(true);
    } catch {
      setPreviewText("Unable to load preview.");
      setPreviewOpen(true);
    } finally {
      setPreviewLoading(false);
    }
  }

  function handleDownload() {
    if (!uploadResult) return;
    window.open(proxyPaths.documentDownload(uploadResult.document_id), "_blank");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFieldErrors({});

    const payload: AnalyzeRequest = { ...form };

    // In upload mode, use document_id instead of curriculum_text
    if (mode === "upload") {
      delete payload.curriculum_text;
      if (!uploadResult) {
        setFieldErrors({ file: "Upload a document first" });
        return;
      }
    } else {
      delete payload.document_id;
    }

    const result = AnalyzeRequestSchema.safeParse(payload);
    if (!result.success) {
      const errs: Partial<Record<string, string>> = {};
      for (const issue of result.error.issues) {
        const key = String(issue.path[0] ?? "curriculum_text");
        if (!errs[key]) errs[key] = issue.message;
      }
      setFieldErrors(errs);
      return;
    }

    analyzeMutation.mutate(result.data, {
      onSuccess: (resp) => {
        saveRecentAnalysis({
          analysis_run_id: resp.analysis_run_id,
          title: form.title || "Untitled",
          subject: form.subject || "",
          grade_band: form.grade_band || "",
          created_at: new Date().toISOString(),
          workspace_id:
            typeof window !== "undefined"
              ? localStorage.getItem("workspace_id") ?? undefined
              : undefined,
        });
      },
    });
  }

  /* ---- success state ---- */

  if (analyzeMutation.isSuccess) {
    const data = analyzeMutation.data as AnalyzeResponse;
    return (
      <div className="flex flex-col items-center gap-6 py-12 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#10B981]/10">
          <svg
            className="h-8 w-8 text-[#10B981]"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-2xl font-semibold text-gray-900">Analysis Submitted</h2>
        <p className="text-sm text-gray-500">
          Run ID:{" "}
          <code className="rounded bg-gray-100 px-2 py-0.5 text-xs font-mono text-[#4F46E5]">
            {data.analysis_run_id}
          </code>
        </p>
        <Link
          href={`/results/${data.analysis_run_id}`}
          className="inline-flex items-center gap-2 rounded-lg bg-[#4F46E5] px-6 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[#4338CA]"
        >
          View Results
          <span aria-hidden="true">&rarr;</span>
        </Link>
        <button
          type="button"
          onClick={() => {
            analyzeMutation.reset();
            setUploadResult(null);
          }}
          className="text-sm text-gray-400 underline-offset-2 hover:text-gray-600 hover:underline"
        >
          Submit another
        </button>
      </div>
    );
  }

  /* ---- form ---- */

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Metadata fields */}
      {(["title", "subject", "grade_band"] as const).map((name) => (
        <div key={name} className="flex flex-col gap-1.5">
          <label htmlFor={name} className="text-sm font-medium text-gray-700">
            {name === "grade_band" ? "Grade Band" : name.charAt(0).toUpperCase() + name.slice(1)}
            <span className="ml-0.5 text-[#4F46E5]">*</span>
          </label>
          <input
            id={name}
            type="text"
            placeholder={
              name === "title"
                ? "e.g. Grade 5 Science Unit"
                : name === "subject"
                  ? "e.g. Science"
                  : "e.g. 3-5"
            }
            value={form[name] ?? ""}
            onChange={(e) => handleChange(name, e.target.value)}
            className={`${INPUT_BASE} ${fieldErrors[name] ? INPUT_ERR : INPUT_OK}`}
          />
          {fieldErrors[name] && (
            <p className="text-xs text-red-500">{fieldErrors[name]}</p>
          )}
        </div>
      ))}

      {/* ── Mode toggle ───────────────────────────────────────────── */}
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-gray-700">
          Curriculum Content<span className="ml-0.5 text-[#4F46E5]">*</span>
        </span>
        <div className="inline-flex self-start rounded-lg border border-gray-200 p-0.5">
          {(["paste", "upload"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => switchMode(m)}
              className={`rounded-md px-3.5 py-1.5 text-xs font-medium transition ${
                mode === m
                  ? "bg-[#4F46E5] text-white shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {m === "paste" ? "Paste Text" : "Upload File"}
            </button>
          ))}
        </div>
      </div>

      {/* ── Paste mode ────────────────────────────────────────────── */}
      {mode === "paste" && (
        <div className="flex flex-col gap-1.5">
          <textarea
            id="curriculum_text"
            rows={6}
            placeholder="Paste full curriculum text here (min 20 chars)…"
            value={form.curriculum_text ?? ""}
            onChange={(e) => handleChange("curriculum_text", e.target.value)}
            className={`resize-y ${INPUT_BASE} ${fieldErrors.curriculum_text ? INPUT_ERR : INPUT_OK}`}
          />
          {fieldErrors.curriculum_text && (
            <p className="text-xs text-red-500">{fieldErrors.curriculum_text}</p>
          )}
        </div>
      )}

      {/* ── Upload mode ───────────────────────────────────────────── */}
      {mode === "upload" && (
        <div className="flex flex-col gap-3">
          {/* File picker + upload button */}
          <div className="flex items-center gap-3">
            <label
              htmlFor="file-upload"
              className={`flex flex-1 cursor-pointer items-center gap-2 rounded-lg border border-dashed px-3.5 py-2.5 text-sm transition ${
                fieldErrors.file
                  ? "border-red-400 bg-red-50"
                  : "border-gray-300 bg-gray-50 hover:border-[#4F46E5]/40"
              }`}
            >
              <svg
                className="h-4 w-4 shrink-0 text-gray-400"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 16V4m0 0l-4 4m4-4l4 4M4 20h16"
                />
              </svg>
              <span className="truncate text-gray-500">
                {fileRef.current?.files?.[0]?.name ?? "Choose file (PDF, Word, Text, etc.)…"}
              </span>
              <input
                ref={fileRef}
                id="file-upload"
                type="file"
                accept=".pdf,.doc,.docx,.txt,.md,.rtf,.html"
                className="sr-only"
                onChange={() => {
                  setFieldErrors((prev) => ({ ...prev, file: undefined }));
                  setUploadResult(null);
                  // Force re-render to show filename
                  setForm((prev) => ({ ...prev }));
                }}
              />
            </label>

            <button
              type="button"
              onClick={handleUpload}
              disabled={uploadMutation.isPending}
              className="shrink-0 rounded-lg bg-[#10B981] px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[#059669] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {uploadMutation.isPending ? "Uploading…" : "Upload"}
            </button>
          </div>

          {fieldErrors.file && (
            <p className="text-xs text-red-500">{fieldErrors.file}</p>
          )}

          {/* Upload error */}
          {uploadMutation.isError && (() => {
            const err = uploadMutation.error;
            const body = err.body as Record<string, unknown> | null;
            const detail = body?.error ?? body?.detail ?? err.message;
            return (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
                <p className="font-medium">Upload failed ({err.status})</p>
                <p className="mt-0.5 text-xs">{String(detail)}</p>
              </div>
            );
          })()}

          {/* Extracted text preview */}
          {uploadResult && (
            <div className="flex flex-col gap-2">
              {/* Status badge + filename + size */}
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                    uploadResult.extraction_status === "EXTRACTED"
                      ? "bg-[#10B981]/10 text-[#10B981]"
                      : "bg-amber-100 text-amber-600"
                  }`}
                >
                  {uploadResult.extraction_status === "EXTRACTED"
                    ? "Extracted"
                    : "Stored (no text)"}
                </span>
                <span className="truncate text-xs text-gray-400 font-mono">
                  {uploadResult.filename}
                </span>
                {uploadResult.size_bytes != null && (
                  <span className="text-[11px] text-gray-300">
                    {(uploadResult.size_bytes / 1024).toFixed(0)} KB
                  </span>
                )}
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-2">
                {uploadResult.extraction_status === "EXTRACTED" && (
                  <button
                    type="button"
                    onClick={handlePreview}
                    disabled={previewLoading}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-[#4F46E5]/20 bg-[#4F46E5]/5 px-3 py-1.5 text-xs font-medium text-[#4F46E5] transition hover:bg-[#4F46E5]/10 disabled:opacity-50"
                  >
                    {previewLoading ? (
                      <>
                        <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Loading…
                      </>
                    ) : previewOpen ? (
                      "Hide Preview"
                    ) : (
                      "Preview Extracted Text"
                    )}
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleDownload}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-50"
                >
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V3" />
                  </svg>
                  Download Original
                </button>
              </div>

              {/* Collapsible preview */}
              {previewOpen && previewText !== null && (
                <textarea
                  readOnly
                  rows={8}
                  value={previewText}
                  className="resize-y rounded-lg border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm text-gray-600 shadow-sm outline-none"
                />
              )}

              {/* Extraction not possible message */}
              {uploadResult.extraction_status !== "EXTRACTED" && (
                <p className="rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-sm text-amber-700">
                  Text could not be extracted from this file. You may paste
                  curriculum text manually instead.
                </p>
              )}

              {/* Warnings */}
              {uploadResult.warnings && uploadResult.warnings.length > 0 && (
                <ul className="space-y-0.5 text-xs text-amber-600">
                  {uploadResult.warnings.map((w, i) => (
                    <li key={i}>⚠ {w}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Rubric (optional, both modes) ─────────────────────────── */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="rubric_text" className="text-sm font-medium text-gray-700">
          Rubric Text (optional)
        </label>
        <textarea
          id="rubric_text"
          rows={4}
          placeholder="Paste rubric text here…"
          value={form.rubric_text ?? ""}
          onChange={(e) => handleChange("rubric_text", e.target.value)}
          className={`resize-y ${INPUT_BASE} ${INPUT_OK}`}
        />
      </div>

      {/* ── Mutation-level error ───────────────────────────────────── */}
      {analyzeMutation.isError && (() => {
        const err = analyzeMutation.error;
        const isApi = err instanceof ApiError;
        const status = isApi ? err.status : null;
        const body = isApi ? (err.body as Record<string, unknown> | null) : null;

        let summary = err.message;
        if (status === 502) {
          summary = "Cannot reach backend — is the API server running?";
        } else if (body?.detail && typeof body.detail === "string") {
          summary = body.detail;
        } else if (body?.error && typeof body.error === "string") {
          summary = body.error;
        }

        // 422 validation: pull out field-level messages
        const validationErrors: string[] = [];
        if (status === 422 && Array.isArray(body?.detail)) {
          for (const issue of body.detail as Array<{ loc?: unknown[]; msg?: string }>) {
            const loc = Array.isArray(issue.loc) ? issue.loc.join(" → ") : "";
            validationErrors.push(`${loc}: ${issue.msg ?? JSON.stringify(issue)}`);
          }
        }

        return (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <p className="font-medium">{summary}</p>
            {status != null && (
              <p className="mt-0.5 text-xs text-red-500">HTTP {status}</p>
            )}
            {validationErrors.length > 0 && (
              <ul className="mt-2 list-inside list-disc space-y-0.5 text-xs text-red-600">
                {validationErrors.map((msg, i) => (
                  <li key={i}>{msg}</li>
                ))}
              </ul>
            )}
            {body != null && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-red-400 hover:text-red-600">
                  Raw response
                </summary>
                <pre className="mt-1 max-h-40 overflow-auto rounded bg-red-100 p-2 text-[11px] text-red-800">
                  {JSON.stringify(body, null, 2)}
                </pre>
              </details>
            )}
          </div>
        );
      })()}

      {/* ── Submit ─────────────────────────────────────────────────── */}
      <button
        type="submit"
        disabled={analyzeMutation.isPending}
        className="w-full rounded-lg bg-[#4F46E5] px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[#4338CA] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {analyzeMutation.isPending ? (
          <span className="inline-flex items-center gap-2">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Analyzing…
          </span>
        ) : (
          "Run Analysis"
        )}
      </button>
    </form>
  );
}
