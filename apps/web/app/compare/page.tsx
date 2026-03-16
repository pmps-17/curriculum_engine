"use client";

import { useCallback, useMemo, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import CompareSelector from "@/components/CompareSelector";
import CompareGrid from "@/components/CompareGrid";
import { useAnalysisRunsQuery } from "@/features/analysisRuns/hooks";
import { apiFetch } from "@/lib/api";
import { proxyPaths } from "@/lib/config";
import type { AnalysisResults } from "@/features/results/hooks";

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function ComparePage() {
  /* ---- workspace id from localStorage ---------------------------- */
  const wsId =
    typeof window !== "undefined"
      ? localStorage.getItem("workspace_id") ?? ""
      : "";

  /* ---- server-backed analysis run list --------------------------- */
  const {
    data: runs,
    isLoading: runsLoading,
    error: runsError,
  } = useAnalysisRunsQuery(wsId);

  /** Map backend items to the shape CompareSelector / CompareGrid expect. */
  const analyses = useMemo(
    () =>
      (runs ?? []).map((r) => ({
        analysis_run_id: r.analysis_run_id,
        title: r.title ?? "",
        subject: r.subject ?? "",
        grade_band: r.grade_band ?? "",
        created_at: r.created_at,
        workspace_id: wsId,
      })),
    [runs, wsId],
  );

  /* ---- selection state ------------------------------------------- */
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [comparing, setComparing] = useState(false);

  const toggle = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 5) next.add(id);
      return next;
    });
  }, []);

  const startCompare = useCallback(() => setComparing(true), []);
  const goBack = useCallback(() => setComparing(false), []);

  /* ---- parallel result fetches ----------------------------------- */
  const selectedIds = useMemo(() => Array.from(selected), [selected]);

  const queries = useQueries({
    queries: comparing
      ? selectedIds.map((id) => ({
          queryKey: ["results", id] as const,
          queryFn: () =>
            apiFetch<AnalysisResults>(proxyPaths.results(id), {
              method: "GET",
            }),
          retry: 1,
          staleTime: 5 * 60 * 1000,
        }))
      : [],
  });

  /* ---- build column state for CompareGrid ------------------------ */
  const columns = useMemo(
    () =>
      selectedIds.map((id, i) => ({
        meta: analyses.find((a) => a.analysis_run_id === id)!,
        data: queries[i]?.data,
        isLoading: queries[i]?.isLoading ?? true,
        error: queries[i]?.error ?? null,
        refetch: queries[i]?.refetch ?? (() => {}),
      })),
    [selectedIds, queries, analyses],
  );

  /* ---- render ---------------------------------------------------- */
  return (
    <section className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">
        Compare Coverage
      </h1>
      <p className="mb-8 text-sm text-gray-500">
        Select 2–5 analyses from this workspace to compare pillar scores
        side-by-side.
      </p>

      {runsLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-[#4F46E5]" />
          <span className="ml-3 text-sm text-gray-500">Loading analyses…</span>
        </div>
      ) : runsError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-6 text-center text-sm text-red-600">
          Failed to load analyses: {runsError.message}
        </div>
      ) : !comparing ? (
        <CompareSelector
          analyses={analyses}
          selected={selected}
          onToggle={toggle}
          onCompare={startCompare}
        />
      ) : (
        <CompareGrid columns={columns} onBack={goBack} />
      )}
    </section>
  );
}
