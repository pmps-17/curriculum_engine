"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { AnalyzeRequestSchema, type AnalyzeRequest } from "@/lib/schemas";
import { useAnalyzeMutation, type AnalyzeResponse } from "@/features/analyze/hooks";
import { uploadDocument, type UploadResponse } from "@/lib/documents";
import { ApiError } from "@/lib/api";
import { saveRecentAnalysis } from "@/lib/recentAnalyses";

/* ------------------------------------------------------------------ */
/*  Shared input style                                                */
/* ------------------------------------------------------------------ */

const INPUT_BASE =
  "rounded-lg border px-3.5 py-2.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:ring-2 focus:ring-[#4F46E5]/30";
const INPUT_OK = "border-gray-200 focus:border-[#4F46E5]";
const INPUT_ERR = "border-red-400 focus:border-red-400";

type Mode = "paste" | "upload";

/* ------------------------------------------------------------------ */
/*  Props                                                             */
/* ------------------------------------------------------------------ */

interface AnalyzeFormProps {
  /** Organization ID (used for uploads) */
  organizationId?: string;
  /** Callback after a successful submission */
  onSuccess?: () => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function AnalyzeForm({
  organizationId,
  onSuccess,
}: AnalyzeFormProps = {}) {
  const [mode, setMode] = useState<Mode>("upload");

  const [form, setForm] = useState<AnalyzeRequest>({
    title: "",
    subject: "",
    grade_band: "",
    curriculum_text: "",
    rubric_text: "",
  });

  /** Optional description — UI only (no backend column yet). */
  const [description, setDescription] = useState("");

  const [fieldErrors, setFieldErrors] = useState<Partial<Record<string, string>>>({});

  // Upload state — multiple files
  const fileRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadResults, setUploadResults] = useState<UploadResponse[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const analyzeMutation = useAnalyzeMutation();

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
    setSelectedFiles([]);
    setUploadResults([]);
    setUploadError(null);
  }

  /** Upload all selected files sequentially via reusable helper. */
  async function handleUploadSubmit() {
    if (selectedFiles.length === 0) {
      setFieldErrors((prev) => ({ ...prev, file: "Select at least one file" }));
      return;
    }
    setFieldErrors((prev) => ({ ...prev, file: undefined }));
    setUploadError(null);

    const orgId =
      organizationId ||
      (typeof window !== "undefined"
        ? localStorage.getItem("organization_id") ?? ""
        : "");

    if (!orgId) {
      setUploadError("No organization selected.");
      return;
    }

    setUploading(true);
    const results: UploadResponse[] = [];
    try {
      for (const file of selectedFiles) {
        const res = await uploadDocument(orgId, file, {
          title: form.title || undefined,
          subject: form.subject || undefined,
          grade_band: form.grade_band || undefined,
        });
        results.push(res);
      }
      setUploadResults(results);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? ((err.body as Record<string, unknown> | null)?.detail ??
              (err.body as Record<string, unknown> | null)?.error ??
              err.message)
          : err instanceof Error
            ? err.message
            : "Upload failed";
      setUploadError(String(msg));
    } finally {
      setUploading(false);
    }
  }

  function handleFileInputChange() {
    const files = fileRef.current?.files;
    if (files && files.length > 0) {
      setSelectedFiles(Array.from(files));
      setFieldErrors((prev) => ({ ...prev, file: undefined }));
      setUploadResults([]);
      setUploadError(null);
    }
  }

  function removeFile(index: number) {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    // Reset the native input so user can re-select
    if (fileRef.current) fileRef.current.value = "";
  }

  /** Handle paste-mode analysis submission. */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFieldErrors({});

    if (mode === "upload") {
      await handleUploadSubmit();
      return;
    }

    // Paste mode — run analysis
    const payload: AnalyzeRequest = { ...form };
    delete payload.document_id;

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
      onSuccess: (resp: AnalyzeResponse) => {
        saveRecentAnalysis({
          analysis_run_id: resp.analysis_run_id,
          title: form.title || "Untitled",
          subject: form.subject || "",
          grade_band: form.grade_band || "",
          created_at: new Date().toISOString(),
          organization_id:
            organizationId ||
            (typeof window !== "undefined"
              ? localStorage.getItem("organization_id") ?? undefined
              : undefined),
        });
        onSuccess?.();
      },
    });
  }

  /* ---- success states ---- */

  // Upload-mode success: show uploaded files and navigate to library
  if (uploadResults.length > 0) {
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
        <h2 className="text-2xl font-semibold text-gray-900">
          {uploadResults.length === 1 ? "Document Uploaded" : `${uploadResults.length} Documents Uploaded`}
        </h2>

        {/* Per-file results */}
        <ul className="w-full max-w-md space-y-2 text-left">
          {uploadResults.map((r) => (
            <li
              key={r.document_id}
              className="flex items-center gap-2 rounded-lg border border-gray-100 bg-white px-4 py-2.5 text-sm shadow-sm"
            >
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                  r.extraction_status === "EXTRACTED"
                    ? "bg-[#10B981]/10 text-[#10B981]"
                    : "bg-amber-100 text-amber-600"
                }`}
              >
                {r.extraction_status === "EXTRACTED" ? "Extracted" : "Stored"}
              </span>
              <span className="truncate font-mono text-xs text-gray-500">
                {r.filename}
              </span>
              {r.size_bytes != null && (
                <span className="ml-auto text-[11px] text-gray-300">
                  {(r.size_bytes / 1024).toFixed(0)} KB
                </span>
              )}
            </li>
          ))}
        </ul>

        <button
          type="button"
          onClick={() => onSuccess?.()}
          className="inline-flex items-center gap-2 rounded-lg bg-[#4F46E5] px-6 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[#4338CA]"
        >
          Back to Library
          <span aria-hidden="true">&rarr;</span>
        </button>
        <button
          type="button"
          onClick={() => {
            setUploadResults([]);
            setSelectedFiles([]);
            if (fileRef.current) fileRef.current.value = "";
          }}
          className="text-sm text-gray-400 underline-offset-2 hover:text-gray-600 hover:underline"
        >
          Upload more
        </button>
      </div>
    );
  }

  // Paste-mode analysis success
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
            {mode === "paste" && <span className="ml-0.5 text-[#4F46E5]">*</span>}
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

      {/* Description (optional) */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="description" className="text-sm font-medium text-gray-700">
          Description <span className="text-xs font-normal text-gray-400">(optional)</span>
        </label>
        <textarea
          id="description"
          rows={2}
          placeholder="Brief description of the curriculum…"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className={`resize-y ${INPUT_BASE} ${INPUT_OK}`}
        />
      </div>

      {/* ── Mode toggle ───────────────────────────────────────────── */}
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-gray-700">
          Curriculum Content
          {mode === "paste" && <span className="ml-0.5 text-[#4F46E5]">*</span>}
        </span>
        <div className="inline-flex self-start rounded-lg border border-gray-200 p-0.5">
          {(["upload", "paste"] as const).map((m) => (
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
              {m === "paste" ? "Paste Text" : "Upload Files"}
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
          {/* File picker (multiple) */}
          <label
            htmlFor="file-upload"
            className={`flex cursor-pointer items-center gap-2 rounded-lg border border-dashed px-3.5 py-2.5 text-sm transition ${
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
              {selectedFiles.length > 0
                ? `${selectedFiles.length} file${selectedFiles.length > 1 ? "s" : ""} selected`
                : "Choose files (PDF, Word, Text)…"}
            </span>
            <input
              ref={fileRef}
              id="file-upload"
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.txt,.md,.rtf,.html"
              className="sr-only"
              onChange={handleFileInputChange}
            />
          </label>

          {fieldErrors.file && (
            <p className="text-xs text-red-500">{fieldErrors.file}</p>
          )}

          {/* Selected file list with remove buttons */}
          {selectedFiles.length > 0 && (
            <ul className="space-y-1">
              {selectedFiles.map((f, i) => (
                <li
                  key={`${f.name}-${i}`}
                  className="flex items-center gap-2 rounded-lg border border-gray-100 bg-white px-3 py-1.5 text-sm"
                >
                  <span className="truncate font-mono text-xs text-gray-500">{f.name}</span>
                  <span className="text-[11px] text-gray-300">
                    {(f.size / 1024).toFixed(0)} KB
                  </span>
                  <button
                    type="button"
                    onClick={() => removeFile(i)}
                    className="ml-auto text-gray-300 hover:text-red-500 transition"
                    aria-label={`Remove ${f.name}`}
                  >
                    <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* Upload error */}
          {uploadError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              <p className="font-medium">Upload failed</p>
              <p className="mt-0.5 text-xs">{uploadError}</p>
            </div>
          )}
        </div>
      )}

      {/* ── Rubric (optional, paste mode only) ─────────────────────── */}
      {mode === "paste" && (
        <div className="flex flex-col gap-1.5">
          <label htmlFor="rubric_text" className="text-sm font-medium text-gray-700">
            Rubric Text <span className="text-xs font-normal text-gray-400">(optional)</span>
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
      )}

      {/* ── Mutation-level error (paste mode) ────────────────────── */}
      {mode === "paste" && analyzeMutation.isError && (() => {
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
        disabled={uploading || analyzeMutation.isPending}
        className="w-full rounded-lg bg-[#4F46E5] px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[#4338CA] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {(uploading || analyzeMutation.isPending) ? (
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
            {uploading ? "Uploading…" : "Analyzing…"}
          </span>
        ) : mode === "upload" ? (
          `Upload ${selectedFiles.length > 1 ? `${selectedFiles.length} Files` : "File"}`
        ) : (
          "Run Analysis"
        )}
      </button>
    </form>
  );
}
