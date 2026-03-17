"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAnalysisRunsQuery } from "@/features/analysisRuns/hooks";
import CurriculumSetRow from "@/components/CurriculumSetRow";
import type { CurriculumSetItem } from "@/components/CurriculumSetRow";
import AddCurriculumSetModal from "@/components/AddCurriculumSetModal";
import ConfirmDeleteModal from "@/components/ConfirmDeleteModal";

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function getOrgId(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("organization_id") ?? "";
}

/* ------------------------------------------------------------------ */
/*  Skeleton loader                                                   */
/* ------------------------------------------------------------------ */

function Skeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {[1, 2, 3, 4].map((n) => (
        <div
          key={n}
          className="h-[72px] rounded-xl border border-gray-200 bg-gray-100"
        />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Empty state                                                       */
/* ------------------------------------------------------------------ */

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-gray-200 bg-white py-16 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#4F46E5]/5">
        <svg
          className="h-7 w-7 text-[#4F46E5]"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 10.5v6m3-3H9m4.06-7.19l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"
          />
        </svg>
      </div>
      <h3 className="mt-4 text-base font-semibold text-gray-900">
        No curriculum sets yet
      </h3>
      <p className="mt-1.5 max-w-xs text-sm text-gray-500">
        Upload a file or paste text to run your first analysis.
      </p>
      <button
        type="button"
        onClick={onAdd}
        className="mt-5 inline-flex items-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA]"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Add Curriculum Set
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function LibraryPage() {
  const orgId = getOrgId();
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error, refetch } = useAnalysisRunsQuery(orgId);

  const [addOpen, setAddOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<CurriculumSetItem | null>(null);

  /* ── Handlers ──────────────────────────────────────────────────── */

  function handleRerun(_item: CurriculumSetItem) {
    // TODO: call re-analyze endpoint once available on backend
    // For now, open the modal pre-filled (or trigger analyze with same document_id)
    alert("Re-run is not yet supported. Please add a new curriculum set instead.");
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    // TODO: call DELETE /api/analysis-runs/:id once available on backend
    // For now, just optimistically remove from UI cache
    queryClient.setQueryData<CurriculumSetItem[]>(
      ["analysis-runs", orgId],
      (old) => old?.filter((r) => r.analysis_run_id !== deleteTarget.analysis_run_id) ?? [],
    );
    setDeleteTarget(null);
  }

  function handleAddSuccess() {
    queryClient.invalidateQueries({ queryKey: ["analysis-runs", orgId] });
  }

  /* ── Coerce AnalysisRunItem → CurriculumSetItem ────────────────── */
  const items: CurriculumSetItem[] = (data ?? []).map((r) => ({
    analysis_run_id: r.analysis_run_id,
    title: r.title ?? "Untitled",
    subject: r.subject ?? "",
    grade_band: r.grade_band ?? "",
    status: r.status,
    created_at: r.created_at,
    document_id: r.document_id ?? null,
  }));

  return (
    <main className="min-h-screen bg-gray-50">
      {/* ── Header ────────────────────────────────────────────────── */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-[1000px] items-center justify-between px-6 py-6">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-gray-900">
              Curriculum <span className="text-[#4F46E5]">Library</span>
            </h1>
            <p className="mt-0.5 text-xs text-gray-400">
              All curriculum sets for your organization.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setAddOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA]"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Add Curriculum Set
          </button>
        </div>
      </header>

      {/* ── Body ──────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-[1000px] px-6 py-8">
        {/* Loading */}
        {isLoading && <Skeleton />}

        {/* Error */}
        {isError && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center space-y-3">
            <p className="text-sm text-red-600">
              {error?.message ?? "Failed to load curriculum sets."}
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-[#4338CA]"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !isError && items.length === 0 && (
          <EmptyState onAdd={() => setAddOpen(true)} />
        )}

        {/* Curriculum set list */}
        {items.length > 0 && (
          <div className="space-y-3">
            {items.map((item) => (
              <CurriculumSetRow
                key={item.analysis_run_id}
                item={item}
                onRerun={handleRerun}
                onDelete={setDeleteTarget}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Add modal ─────────────────────────────────────────────── */}
      <AddCurriculumSetModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onSuccess={handleAddSuccess}
      />

      {/* ── Delete confirmation ───────────────────────────────────── */}
      <ConfirmDeleteModal
        open={!!deleteTarget}
        title={deleteTarget?.title ?? ""}
        onConfirm={handleDeleteConfirm}
        onClose={() => setDeleteTarget(null)}
      />
    </main>
  );
}
