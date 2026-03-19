"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { proxyPaths } from "@/lib/config";
import { apiFetch } from "@/lib/api";
import { deleteDocument } from "@/lib/documents";
import type { DocumentLibraryItem as LibraryItem } from "@/lib/documents";
import DocumentActionsMenu from "@/components/DocumentActionsMenu";
import EditDocumentModal from "@/components/EditDocumentModal";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

export type { LibraryItem };

interface Props {
  items: LibraryItem[];
  organizationId: string;
  /** Called after a mutation so parent can re-fetch */
  onMutated: () => void;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function displayTitle(item: LibraryItem): string {
  return item.title || item.filename;
}

function statusBadge(status: string) {
  switch (status) {
    case "EXTRACTED":
      return (
        <span className="rounded-full bg-[#10B981]/10 px-2 py-0.5 text-[11px] font-semibold text-[#10B981]">
          Extracted
        </span>
      );
    case "REJECTED":
      return (
        <span className="rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-600">
          Rejected
        </span>
      );
    default:
      return (
        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-600">
          Stored
        </span>
      );
  }
}

function analysisBadge(status: string | null) {
  if (!status) return null;
  const map: Record<string, { label: string; colors: string }> = {
    completed: { label: "Analyzed",  colors: "bg-[#10B981]/10 text-[#10B981]" },
    running:   { label: "Running",   colors: "bg-blue-100 text-blue-600" },
    queued:    { label: "Running",   colors: "bg-blue-100 text-blue-600" },
    pending:   { label: "Pending",   colors: "bg-gray-100 text-gray-500" },
    failed:    { label: "Failed",    colors: "bg-red-100 text-red-600" },
  };
  const entry = map[status] ?? { label: status, colors: "bg-gray-100 text-gray-500" };
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${entry.colors}`}
    >
      {entry.label}
    </span>
  );
}

function formatDate(iso: string) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatSize(bytes: number | null) {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** True when the row should be clickable (navigates to the report). */
function hasCompletedReport(item: LibraryItem): boolean {
  return item.latest_analysis_status === "completed" && !!item.latest_analysis_run_id;
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function DocumentLibraryTable({
  items,
  organizationId,
  onMutated,
}: Props) {
  const router = useRouter();

  // Edit modal state
  const [editTarget, setEditTarget] = useState<LibraryItem | null>(null);

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<LibraryItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  /* ── Run Analysis ─────────────────────────────────────────────── */

  async function handleRunAnalysis(item: LibraryItem) {
    try {
      const resp = await apiFetch<{ analysis_run_id: string }>(
        proxyPaths.analyze,
        {
          method: "POST",
          body: {
            document_id: item.document_id,
            title: item.title || item.filename,
            subject: item.subject || "General",
            grade_band: item.grade_band || "K-12",
            organization_id: organizationId,
          },
        },
      );
      router.push(`/results/${resp.analysis_run_id}`);
    } catch (err) {
      console.error("Run analysis failed:", err);
      alert("Failed to start analysis. Check the console for details.");
    }
  }

  /* ── View Report ──────────────────────────────────────────────── */

  function handleViewReport(item: LibraryItem) {
    if (item.latest_analysis_run_id) {
      router.push(`/results/${item.latest_analysis_run_id}`);
    }
  }

  /* ── Delete ───────────────────────────────────────────────────── */

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteDocument(deleteTarget.document_id);
      setDeleteTarget(null);
      onMutated();
    } catch (err) {
      console.error("Delete failed:", err);
      alert(err instanceof Error ? err.message : "Failed to delete document.");
    } finally {
      setDeleting(false);
    }
  }

  /* ── Empty state ──────────────────────────────────────────────── */

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-gray-200 bg-white py-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#4F46E5]/5">
          <svg className="h-7 w-7 text-[#4F46E5]" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
        </div>
        <h3 className="mt-4 text-base font-semibold text-gray-900">
          No documents yet
        </h3>
        <p className="mt-1.5 max-w-xs text-sm text-gray-500">
          Upload a curriculum document to get started.
        </p>
      </div>
    );
  }

  /* ── Table ────────────────────────────────────────────────────── */

  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Title</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Subject</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Grade</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Analysis</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Size</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Uploaded</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((item) => {
              const clickable = hasCompletedReport(item);
              return (
              <tr
                key={item.document_id}
                onClick={clickable ? (e: React.MouseEvent<HTMLTableRowElement>) => {
                  const target = e.target as HTMLElement;
                  if (target.closest("[data-row-action]")) return;
                  router.push(`/results/${item.latest_analysis_run_id}`);
                } : undefined}
                className={`transition ${
                  clickable
                    ? "cursor-pointer hover:bg-indigo-50/60"
                    : "hover:bg-gray-50/60"
                }`}
              >
                {/* Title */}
                <td className="max-w-[240px] truncate px-4 py-3 font-medium text-gray-900">
                  {displayTitle(item)}
                </td>

                {/* Subject */}
                <td className="px-4 py-3 text-gray-600">
                  {item.subject || <span className="text-gray-300">—</span>}
                </td>

                {/* Grade */}
                <td className="px-4 py-3 text-gray-600">
                  {item.grade_band || <span className="text-gray-300">—</span>}
                </td>

                {/* Extraction status */}
                <td className="px-4 py-3">{statusBadge(item.extraction_status)}</td>

                {/* Analysis */}
                <td className="px-4 py-3">
                  {item.latest_analysis_run_id ? (
                    <button
                      type="button"
                      data-row-action
                      onClick={(e) => { e.stopPropagation(); handleViewReport(item); }}
                      className="hover:underline"
                    >
                      {analysisBadge(item.latest_analysis_status)}
                    </button>
                  ) : (
                    <span className="text-xs text-gray-300">none</span>
                  )}
                </td>

                {/* Size */}
                <td className="px-4 py-3 text-gray-500 tabular-nums">
                  {formatSize(item.size_bytes)}
                </td>

                {/* Uploaded */}
                <td className="whitespace-nowrap px-4 py-3 text-gray-500">
                  {formatDate(item.created_at)}
                </td>

                {/* Actions */}
                <td className="px-4 py-3 text-right" data-row-action>
                  <DocumentActionsMenu
                    hasReport={item.latest_analysis_status === "completed" && !!item.latest_analysis_run_id}
                    onRunAnalysis={() => handleRunAnalysis(item)}
                    onViewReport={() => handleViewReport(item)}
                    onRename={() => setEditTarget(item)}
                    onDelete={() => setDeleteTarget(item)}
                  />
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── Edit modal ────────────────────────────────────────────── */}
      <EditDocumentModal
        open={!!editTarget}
        item={editTarget}
        onClose={() => setEditTarget(null)}
        onSaved={onMutated}
      />

      {/* ── Delete confirmation ───────────────────────────────────── */}
      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => setDeleteTarget(null)}
        >
          <div
            className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-gray-900">Delete Document</h3>
            <p className="mt-2 text-sm text-gray-600">
              Are you sure you want to delete{" "}
              <strong>{displayTitle(deleteTarget)}</strong>? This action cannot
              be undone.
            </p>
            <div className="mt-5 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                disabled={deleting}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-red-700 disabled:opacity-60"
              >
                {deleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
