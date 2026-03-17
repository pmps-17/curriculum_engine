"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { AnalyzeRequestSchema, type AnalyzeRequest } from "@/lib/schemas";
import { useAnalyzeMutation, type AnalyzeResponse } from "@/features/analyze/hooks";
import { useUploadMutation, type UploadResponse } from "@/features/analyze/uploadHooks";
import { ApiError } from "@/lib/api";
import { saveRecentAnalysis } from "@/lib/recentAnalyses";

/* ------------------------------------------------------------------ */
/*  Shared styles                                                     */
/* ------------------------------------------------------------------ */

const INPUT =
  "h-10 rounded-lg border border-gray-200 bg-white px-3.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20";
const INPUT_ERR =
  "h-10 rounded-lg border border-red-400 bg-white px-3.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-red-400 focus:ring-2 focus:ring-red-200";

type Tab = "upload" | "paste";

/* ------------------------------------------------------------------ */
/*  Props                                                             */
/* ------------------------------------------------------------------ */

interface Props {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function AddCurriculumSetModal({ open, onClose, onSuccess }: Props) {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("upload");

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

  const analyzeMutation = useAnalyzeMutation();
  const uploadMutation = useUploadMutation();

  if (!open) return null;

  /* ── helpers ───────────────────────────────────────────────────── */

  function handleChange(name: keyof AnalyzeRequest, value: string) {
    setForm((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
  }

  function switchTab(next: Tab) {
    setTab(next);
    setFieldErrors({});
    setForm((prev) => ({ ...prev, curriculum_text: "", document_id: undefined }));
    setUploadResult(null);
    uploadMutation.reset();
  }

  async function handleUploadFile() {
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
        setForm((prev) => ({ ...prev, document_id: data.document_id }));
      },
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFieldErrors({});

    const payload: AnalyzeRequest = { ...form };

    if (tab === "upload") {
      delete payload.curriculum_text;
      if (!uploadResult) {
        setFieldErrors({ file: "Upload a file first" });
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
      onSuccess: (resp: AnalyzeResponse) => {
        saveRecentAnalysis({
          analysis_run_id: resp.analysis_run_id,
          title: form.title || "Untitled",
          subject: form.subject || "",
          grade_band: form.grade_band || "",
          created_at: new Date().toISOString(),
          organization_id:
            typeof window !== "undefined"
              ? localStorage.getItem("organization_id") ?? undefined
              : undefined,
        });
        // Navigate to results
        handleClose();
        onSuccess();
        router.push(`/results/${resp.analysis_run_id}`);
      },
    });
  }

  function handleClose() {
    setForm({ title: "", subject: "", grade_band: "", curriculum_text: "", rubric_text: "" });
    setFieldErrors({});
    setUploadResult(null);
    setTab("upload");
    analyzeMutation.reset();
    uploadMutation.reset();
    onClose();
  }

  function handleBackdrop(e: React.MouseEvent) {
    if (e.target === e.currentTarget) handleClose();
  }

  /* ── render ────────────────────────────────────────────────────── */

  const analyzeErr = analyzeMutation.error;
  const analyzeErrMsg = (() => {
    if (!analyzeErr) return null;
    if (analyzeErr instanceof ApiError) {
      const body = analyzeErr.body as Record<string, unknown> | null;
      if (analyzeErr.status === 502) return "Cannot reach backend — is the API server running?";
      if (body?.detail && typeof body.detail === "string") return body.detail;
      if (body?.error && typeof body.error === "string") return body.error;
    }
    return analyzeErr.message;
  })();

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 backdrop-blur-sm px-4 py-10"
      onClick={handleBackdrop}
    >
      <div className="w-full max-w-xl rounded-2xl border border-gray-200/80 bg-white shadow-xl">
        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Add Curriculum Set</h2>
            <p className="mt-0.5 text-xs text-gray-500">Upload a file or paste text to run analysis.</p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-lg p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* ── Body ────────────────────────────────────────────────── */}
        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          {/* Metadata row */}
          <div className="grid gap-3 sm:grid-cols-3">
            {(["title", "subject", "grade_band"] as const).map((name) => (
              <div key={name} className="flex flex-col gap-1">
                <label className="text-xs font-medium text-gray-600">
                  {name === "grade_band" ? "Grade Band" : name.charAt(0).toUpperCase() + name.slice(1)}
                  <span className="ml-0.5 text-[#4F46E5]">*</span>
                </label>
                <input
                  type="text"
                  value={form[name] ?? ""}
                  onChange={(e) => handleChange(name, e.target.value)}
                  placeholder={name === "title" ? "e.g. Grade 5 Science" : name === "subject" ? "Science" : "3-5"}
                  className={fieldErrors[name] ? INPUT_ERR : INPUT}
                />
                {fieldErrors[name] && <p className="text-[11px] text-red-500">{fieldErrors[name]}</p>}
              </div>
            ))}
          </div>

          {/* ── Tab toggle ────────────────────────────────────────── */}
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-gray-600">
              Curriculum Content<span className="ml-0.5 text-[#4F46E5]">*</span>
            </span>
            <div className="inline-flex self-start rounded-lg border border-gray-200 p-0.5">
              {(["upload", "paste"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => switchTab(t)}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                    tab === t
                      ? "bg-[#4F46E5] text-white shadow-sm"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {t === "upload" ? "Upload File" : "Paste Text"}
                </button>
              ))}
            </div>
          </div>

          {/* ── Upload tab ────────────────────────────────────────── */}
          {tab === "upload" && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-3">
                <label
                  htmlFor="modal-file-upload"
                  className={`flex flex-1 cursor-pointer items-center gap-2 rounded-lg border border-dashed px-3.5 py-2.5 text-sm transition ${
                    fieldErrors.file
                      ? "border-red-400 bg-red-50"
                      : "border-gray-300 bg-gray-50 hover:border-[#4F46E5]/40"
                  }`}
                >
                  <svg className="h-4 w-4 shrink-0 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0l-4 4m4-4l4 4M4 20h16" />
                  </svg>
                  <span className="truncate text-gray-500">
                    {fileRef.current?.files?.[0]?.name ?? "Choose file (PDF, Word, Text)…"}
                  </span>
                  <input
                    ref={fileRef}
                    id="modal-file-upload"
                    type="file"
                    accept=".pdf,.doc,.docx,.txt,.md,.rtf,.html"
                    className="sr-only"
                    onChange={() => {
                      setFieldErrors((prev) => ({ ...prev, file: undefined }));
                      setUploadResult(null);
                      setForm((prev) => ({ ...prev }));
                    }}
                  />
                </label>
                <button
                  type="button"
                  onClick={handleUploadFile}
                  disabled={uploadMutation.isPending}
                  className="shrink-0 rounded-lg bg-[#10B981] px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[#059669] disabled:opacity-60"
                >
                  {uploadMutation.isPending ? "Uploading…" : "Upload"}
                </button>
              </div>
              {fieldErrors.file && <p className="text-[11px] text-red-500">{fieldErrors.file}</p>}

              {/* Upload error */}
              {uploadMutation.isError && (
                <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
                  Upload failed: {(uploadMutation.error as ApiError)?.message ?? "Unknown error"}
                </p>
              )}

              {/* Upload success badge */}
              {uploadResult && (
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                    uploadResult.extraction_status === "EXTRACTED"
                      ? "bg-[#10B981]/10 text-[#10B981]"
                      : "bg-amber-100 text-amber-600"
                  }`}>
                    {uploadResult.extraction_status === "EXTRACTED" ? "Text extracted" : "Stored (no text)"}
                  </span>
                  <span className="truncate text-xs text-gray-400 font-mono">{uploadResult.filename}</span>
                </div>
              )}
            </div>
          )}

          {/* ── Paste tab ─────────────────────────────────────────── */}
          {tab === "paste" && (
            <div className="flex flex-col gap-1.5">
              <textarea
                rows={5}
                placeholder="Paste full curriculum text here (min 20 chars)…"
                value={form.curriculum_text ?? ""}
                onChange={(e) => handleChange("curriculum_text", e.target.value)}
                className={`resize-y rounded-lg border px-3.5 py-2.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:ring-2 focus:ring-[#4F46E5]/20 ${
                  fieldErrors.curriculum_text ? "border-red-400" : "border-gray-200 focus:border-[#4F46E5]"
                }`}
              />
              {fieldErrors.curriculum_text && (
                <p className="text-[11px] text-red-500">{fieldErrors.curriculum_text}</p>
              )}
            </div>
          )}

          {/* ── Rubric (optional) ─────────────────────────────────── */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">Rubric Text (optional)</label>
            <textarea
              rows={3}
              placeholder="Paste rubric text here…"
              value={form.rubric_text ?? ""}
              onChange={(e) => handleChange("rubric_text", e.target.value)}
              className="resize-y rounded-lg border border-gray-200 px-3.5 py-2.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20"
            />
          </div>

          {/* ── Mutation error ────────────────────────────────────── */}
          {analyzeMutation.isError && analyzeErrMsg && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              {analyzeErrMsg}
            </div>
          )}

          {/* ── Footer ────────────────────────────────────────────── */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              className="h-10 rounded-lg px-4 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={analyzeMutation.isPending}
              className="flex h-10 items-center gap-2 rounded-lg bg-[#4F46E5] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA] disabled:opacity-50"
            >
              {analyzeMutation.isPending ? (
                <>
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Analyzing…
                </>
              ) : (
                "Upload & Run Analysis"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
