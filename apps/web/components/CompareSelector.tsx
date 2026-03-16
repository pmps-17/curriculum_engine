"use client";

import type { RecentAnalysis } from "@/lib/recentAnalyses";

/* ------------------------------------------------------------------ */
/*  Props                                                             */
/* ------------------------------------------------------------------ */

interface Props {
  analyses: RecentAnalysis[];
  selected: Set<string>;
  onToggle: (id: string) => void;
  onCompare: () => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function CompareSelector({
  analyses,
  selected,
  onToggle,
  onCompare,
}: Props) {
  const count = selected.size;

  if (analyses.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
          <svg className="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p className="text-sm text-gray-500">
          No analyses yet in this workspace.
        </p>
        <p className="text-xs text-gray-400">
          Run an analysis from the <a href="/" className="text-[#4F46E5] hover:underline">dashboard</a> first.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              <th className="w-10 px-4 py-3" />
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Subject</th>
              <th className="hidden px-4 py-3 sm:table-cell">Grade</th>
              <th className="hidden px-4 py-3 md:table-cell">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {analyses.map((a) => {
              const checked = selected.has(a.analysis_run_id);
              const disabled = !checked && count >= 5;
              return (
                <tr
                  key={a.analysis_run_id}
                  onClick={() => !disabled && onToggle(a.analysis_run_id)}
                  className={`cursor-pointer transition ${
                    checked
                      ? "bg-[#4F46E5]/5"
                      : disabled
                        ? "opacity-40"
                        : "hover:bg-gray-50"
                  }`}
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={() => onToggle(a.analysis_run_id)}
                      className="h-4 w-4 rounded border-gray-300 text-[#4F46E5] accent-[#4F46E5]"
                    />
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {a.title || "Untitled"}
                    <span className="ml-2 hidden font-mono text-[10px] text-gray-300 lg:inline">
                      {a.analysis_run_id.slice(0, 8)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{a.subject || "—"}</td>
                  <td className="hidden px-4 py-3 text-gray-600 sm:table-cell">
                    {a.grade_band || "—"}
                  </td>
                  <td className="hidden px-4 py-3 text-gray-400 md:table-cell">
                    {formatDate(a.created_at)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Action bar */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-400">
          {count} of {analyses.length} selected (2–5 required)
        </p>
        <button
          type="button"
          disabled={count < 2}
          onClick={onCompare}
          className="rounded-lg bg-[#4F46E5] px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[#4338CA] disabled:cursor-not-allowed disabled:opacity-40"
        >
          Compare {count > 0 ? `(${count})` : ""}
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
