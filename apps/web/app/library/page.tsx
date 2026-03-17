"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useAnalysisRunsQuery, type AnalysisRunItem } from "@/features/analysisRuns/hooks";
import { useAnalyzeMutation } from "@/features/analyze/hooks";
import CurriculumSetRow from "@/components/CurriculumSetRow";
import type { CurriculumSetItem } from "@/components/CurriculumSetRow";
import AddCurriculumSetModal from "@/components/AddCurriculumSetModal";
import EditDetailsModal from "@/components/EditDetailsModal";
import ConfirmDeleteModal from "@/components/ConfirmDeleteModal";

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function getOrgId(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("organization_id") ?? "";
}

/**
 * Group analysis runs by document_id.
 *
 * Each unique document_id (or standalone run without a document)
 * becomes one "Curriculum Set" row.  We keep the latest run's status
 * and created_at, plus a run count.
 */
function groupByDocument(runs: AnalysisRunItem[]): CurriculumSetItem[] {
  const map = new Map<
    string,
    { runs: AnalysisRunItem[]; document_id: string | null }
  >();

  for (const r of runs) {
    // Key: document_id when present, else the run id itself
    const key = r.document_id ?? r.analysis_run_id;
    const entry = map.get(key);
    if (entry) {
      entry.runs.push(r);
    } else {
      map.set(key, { runs: [r], document_id: r.document_id ?? null });
    }
  }

  const items: CurriculumSetItem[] = [];
  for (const [key, { runs: groupRuns, document_id }] of map) {
    // Runs are already sorted newest-first from the backend
    const latest = groupRuns[0];
    // Find the latest completed run (for "View Report")
    const latestCompleted = groupRuns.find(
      (r) => r.status.toLowerCase() === "completed" || r.status.toLowerCase() === "complete",
    );
    items.push({
      id: key,
      latest_run_id: latestCompleted?.analysis_run_id ?? latest.analysis_run_id,
      run_count: groupRuns.length,
      title: latest.title ?? "Untitled",
      subject: latest.subject ?? "",
      grade_band: latest.grade_band ?? "",
      status: latest.status,
      created_at: latest.created_at,
      document_id,
    });
  }

  return items;
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
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error, refetch } = useAnalysisRunsQuery(orgId);
  const analyzeMutation = useAnalyzeMutation();

  const [addOpen, setAddOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<CurriculumSetItem | null>(null);
  const [editTarget, setEditTarget] = useState<CurriculumSetItem | null>(null);
  const [rerunningId, setRerunningId] = useState<string | null>(null);

  // Group raw analysis runs → one row per document
  const items = useMemo(() => groupByDocument(data ?? []), [data]);

  /* ── Re-run analysis using POST /api/v1/analyze ────────────────── */

  function handleRerun(item: CurriculumSetItem) {
    if (!item.document_id) {
      // Text-only runs can't be re-run (no stored document)
      alert("Re-run is only available for file-based curriculum sets.");
      return;
    }
    setRerunningId(item.id);
    analyzeMutation.mutate(
      {
        title: item.title,
        subject: item.subject,
        grade_band: item.grade_band,
        document_id: item.document_id,
      },
      {
        onSuccess: (resp) => {
          setRerunningId(null);
          queryClient.invalidateQueries({ queryKey: ["analysis-runs", orgId] });
          router.push(`/results/${resp.analysis_run_id}`);
        },
        onError: () => {
          setRerunningId(null);
          alert("Re-run failed. Please try again.");
        },
      },
    );
  }

  /* ── Edit details (optimistic cache update) ────────────────────── */

  function handleEditSave(updated: { title: string; subject: string; grade_band: string }) {
    if (!editTarget) return;
    // Optimistically update the query cache
    // TODO: call PATCH /api/v1/documents/:id once available on backend
    queryClient.setQueryData<AnalysisRunItem[]>(
      ["analysis-runs", orgId],
      (old) =>
        (old ?? []).map((r) => {
          const key = r.document_id ?? r.analysis_run_id;
          if (key === editTarget.id) {
            return {
              ...r,
              title: updated.title || r.title,
              subject: updated.subject || r.subject,
              grade_band: updated.grade_band || r.grade_band,
            };
          }
          return r;
        }),
    );
    setEditTarget(null);
  }

  /* ── Delete (optimistic cache removal) ─────────────────────────── */

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    // TODO: call DELETE /api/v1/documents/:id once available on backend
    // For now, optimistically remove all runs belonging to this document
    queryClient.setQueryData<AnalysisRunItem[]>(
      ["analysis-runs", orgId],
      (old) => {
        if (!old) return [];
        return old.filter((r) => {
          const key = r.document_id ?? r.analysis_run_id;
          return key !== deleteTarget.id;
        });
      },
    );
    setDeleteTarget(null);
  }

  /* ── Add success ───────────────────────────────────────────────── */

  function handleAddSuccess() {
    queryClient.invalidateQueries({ queryKey: ["analysis-runs", orgId] });
  }

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

        {/* Re-run spinner overlay */}
        {rerunningId && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-[#4F46E5]/20 bg-[#4F46E5]/5 px-4 py-3 text-sm text-[#4F46E5]">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Re-running analysis…
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
                key={item.id}
                item={item}
                onRerun={handleRerun}
                onEdit={setEditTarget}
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

      {/* ── Edit details modal ────────────────────────────────────── */}
      <EditDetailsModal
        open={!!editTarget}
        initial={{
          title: editTarget?.title ?? "",
          subject: editTarget?.subject ?? "",
          grade_band: editTarget?.grade_band ?? "",
        }}
        onSave={handleEditSave}
        onClose={() => setEditTarget(null)}
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
