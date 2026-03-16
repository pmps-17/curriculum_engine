"use client";

import type { AnalysisResults, PillarScore } from "@/features/results/hooks";
import type { RecentAnalysis } from "@/lib/recentAnalyses";

/* ------------------------------------------------------------------ */
/*  Props                                                             */
/* ------------------------------------------------------------------ */

interface ColumnState {
  meta: RecentAnalysis;
  data?: AnalysisResults;
  isLoading: boolean;
  error?: Error | null;
  refetch: () => void;
}

interface Props {
  columns: ColumnState[];
  onBack: () => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function CompareGrid({ columns, onBack }: Props) {
  /* Gather the union of all pillar codes across every loaded result. */
  const pillarCodes = dedupOrdered(
    columns.flatMap(
      (c) => c.data?.pillar_scores?.map((p) => p.pillar_code ?? "") ?? [],
    ),
  );

  return (
    <div className="space-y-4">
      {/* Back button */}
      <button
        type="button"
        onClick={onBack}
        className="flex items-center gap-1 text-sm text-gray-500 transition hover:text-[#4F46E5]"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Back to selection
      </button>

      {/* Grid */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          {/* Header – one column per analysis */}
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              <th className="sticky left-0 z-10 min-w-[120px] bg-gray-50 px-4 py-3">
                Pillar
              </th>
              {columns.map((c) => (
                <th
                  key={c.meta.analysis_run_id}
                  className="min-w-[160px] px-4 py-3"
                >
                  <span className="block truncate font-semibold normal-case text-gray-800">
                    {c.meta.title || "Untitled"}
                  </span>
                  <span className="mt-0.5 block text-[10px] font-normal normal-case text-gray-400">
                    {c.meta.subject} · {c.meta.grade_band}
                  </span>
                </th>
              ))}
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-100">
            {pillarCodes.length === 0 && !columns.some((c) => c.isLoading) ? (
              <tr>
                <td
                  colSpan={columns.length + 1}
                  className="px-4 py-8 text-center text-sm text-gray-400"
                >
                  No pillar data available.
                </td>
              </tr>
            ) : (
              pillarCodes.map((code) => (
                <tr key={code} className="hover:bg-gray-50/60 transition">
                  <td className="sticky left-0 z-10 bg-white px-4 py-3 font-medium text-gray-900">
                    {pillarLabel(code, columns)}
                  </td>
                  {columns.map((c) => (
                    <td
                      key={c.meta.analysis_run_id}
                      className="px-4 py-3"
                    >
                      <CellContent col={c} pillarCode={code} />
                    </td>
                  ))}
                </tr>
              ))
            )}

            {/* Summary row – best pillar per analysis */}
            {pillarCodes.length > 0 && (
              <tr className="border-t-2 border-gray-200 bg-gray-50/60">
                <td className="sticky left-0 z-10 bg-gray-50/60 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Top Pillar
                </td>
                {columns.map((c) => {
                  const top = bestPillar(c.data);
                  return (
                    <td
                      key={c.meta.analysis_run_id}
                      className="px-4 py-3 text-xs font-medium text-[#10B981]"
                    >
                      {top
                        ? `${top.pillar_name ?? top.pillar_code} (${pct(top.score)})`
                        : "—"}
                    </td>
                  );
                })}
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Cell content                                                      */
/* ------------------------------------------------------------------ */

function CellContent({
  col,
  pillarCode,
}: {
  col: ColumnState;
  pillarCode: string;
}) {
  if (col.isLoading) {
    return (
      <div className="flex items-center gap-2">
        <div className="h-4 w-12 animate-pulse rounded bg-gray-200" />
        <div className="h-3 w-8 animate-pulse rounded bg-gray-100" />
      </div>
    );
  }

  if (col.error) {
    return (
      <div className="flex flex-col gap-1">
        <span className="text-xs text-red-500">Error</span>
        <button
          type="button"
          onClick={() => col.refetch()}
          className="text-[10px] text-[#4F46E5] hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  const pillar = col.data?.pillar_scores?.find(
    (p) => p.pillar_code === pillarCode,
  );

  if (!pillar) {
    return <span className="text-xs text-gray-300">—</span>;
  }

  return (
    <div className="flex items-center gap-2">
      <span className="font-semibold text-gray-900">{pct(pillar.score)}</span>
      <ConfidenceChip value={pillar.confidence} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Confidence chip                                                   */
/* ------------------------------------------------------------------ */

function ConfidenceChip({ value }: { value?: number }) {
  if (value == null) return null;

  const label = value >= 0.8 ? "High" : value >= 0.5 ? "Med" : "Low";
  const color =
    value >= 0.8
      ? "bg-[#10B981]/10 text-[#10B981]"
      : value >= 0.5
        ? "bg-amber-100 text-amber-700"
        : "bg-red-100 text-red-600";

  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${color}`}
    >
      {label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function pct(val?: number): string {
  if (val == null) return "—";
  return `${Math.round(val * 100)}%`;
}

/** Get the human-readable name for a pillar code, falling back to the code. */
function pillarLabel(code: string, columns: ColumnState[]): string {
  for (const c of columns) {
    const p = c.data?.pillar_scores?.find((ps) => ps.pillar_code === code);
    if (p?.pillar_name) return p.pillar_name;
  }
  return code;
}

function bestPillar(data?: AnalysisResults): PillarScore | undefined {
  if (!data?.pillar_scores?.length) return undefined;
  return data.pillar_scores.reduce((a, b) =>
    (b.score ?? 0) > (a.score ?? 0) ? b : a,
  );
}

function dedupOrdered(arr: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const v of arr) {
    if (v && !seen.has(v)) {
      seen.add(v);
      out.push(v);
    }
  }
  return out;
}
