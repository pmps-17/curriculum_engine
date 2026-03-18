"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

export interface CurriculumSetItem {
  /** Primary key for the row — document_id when available, else latest analysis_run_id. */
  id: string;
  /** Latest *completed* analysis run id (null if none completed). */
  latest_run_id: string | null;
  /** Total number of analysis runs for this document. */
  run_count: number;
  title: string;
  subject: string;
  grade_band: string;
  /** Status of the most recent analysis run. */
  status: string;
  created_at: string;
  document_id: string | null;
}

interface CurriculumSetRowProps {
  item: CurriculumSetItem;
  onRerun: (item: CurriculumSetItem) => void;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function statusBadge(status: string) {
  const s = status?.toLowerCase() ?? "";
  if (s === "completed" || s === "complete")
    return { bg: "bg-[#10B981]/10", text: "text-[#10B981]", label: "Analyzed" };
  if (s === "failed" || s === "error")
    return { bg: "bg-red-100", text: "text-red-600", label: "Failed" };
  if (s === "running" || s === "in_progress" || s === "pending")
    return { bg: "bg-amber-100", text: "text-amber-600", label: "Running" };
  return { bg: "bg-gray-100", text: "text-gray-500", label: "Uploaded" };
}

function sourceType(docId: string | null): string {
  return docId ? "File" : "Text";
}

function timeAgo(iso: string): string {
  const d = new Date(iso);
  const now = Date.now();
  const diff = now - d.getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function CurriculumSetRow({
  item,
  onRerun,
}: CurriculumSetRowProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    function onClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [menuOpen]);

  const badge = statusBadge(item.status);
  const hasCompletedReport = item.latest_run_id !== null;

  return (
    <div className="group flex items-center gap-4 rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm transition hover:border-gray-300 hover:shadow-md">
      {/* ── Icon ────────────────────────────────────────────────────── */}
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#4F46E5]/5">
        <svg className="h-5 w-5 text-[#4F46E5]" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
      </div>

      {/* ── Main info ───────────────────────────────────────────────── */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h3 className="truncate text-sm font-semibold text-gray-900">
            {item.title || "Untitled"}
          </h3>
          <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${badge.bg} ${badge.text}`}>
            {badge.label}
          </span>
        </div>
        <div className="mt-0.5 flex items-center gap-3 text-[12px] text-gray-400">
          {item.subject && <span>{item.subject}</span>}
          {item.grade_band && (
            <>
              <span className="text-gray-300">·</span>
              <span>{item.grade_band}</span>
            </>
          )}
          <span className="text-gray-300">·</span>
          <span>{sourceType(item.document_id)}</span>
          {item.run_count > 1 && (
            <>
              <span className="text-gray-300">·</span>
              <span>{item.run_count} {item.run_count === 1 ? "analysis" : "analyses"}</span>
            </>
          )}
          <span className="text-gray-300">·</span>
          <span>{timeAgo(item.created_at)}</span>
        </div>
      </div>

      {/* ── View report button ──────────────────────────────────────── */}
      {hasCompletedReport ? (
        <Link
          href={`/results/${item.latest_run_id}`}
          className="hidden shrink-0 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:border-[#4F46E5]/30 hover:text-[#4F46E5] sm:inline-flex"
        >
          View Report
        </Link>
      ) : (
        <span
          className="hidden shrink-0 cursor-default rounded-lg border border-gray-100 px-3 py-1.5 text-xs font-medium text-gray-300 sm:inline-flex"
          title="No completed report yet"
        >
          View Report
        </span>
      )}

      {/* ── 3-dot menu ──────────────────────────────────────────────── */}
      <div className="relative" ref={menuRef}>
        <button
          type="button"
          onClick={() => setMenuOpen(!menuOpen)}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
          aria-label="Actions"
        >
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z" />
          </svg>
        </button>

        {menuOpen && (
          <div className="absolute right-0 z-50 mt-1 w-52 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
            {/* View report */}
            {hasCompletedReport ? (
              <Link
                href={`/results/${item.latest_run_id}`}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-gray-700 transition hover:bg-gray-50"
                onClick={() => setMenuOpen(false)}
              >
                <svg className="h-3.5 w-3.5 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
                </svg>
                View Report
              </Link>
            ) : (
              <span className="flex w-full items-center gap-2 px-3 py-2 text-xs text-gray-300 cursor-default">
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
                </svg>
                <span>View Report <span className="text-[10px] text-gray-300">· no completed report</span></span>
              </span>
            )}

            {/* Re-run analysis */}
            <button
              type="button"
              onClick={() => { setMenuOpen(false); onRerun(item); }}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-gray-700 transition hover:bg-gray-50"
            >
              <svg className="h-3.5 w-3.5 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
              </svg>
              Re-run Analysis
            </button>

            {/* Divider */}
            <div className="my-1 border-t border-gray-100" />

            {/* Edit details — disabled */}
            <span
              className="flex w-full items-center gap-2 px-3 py-2 text-xs text-gray-300 cursor-default"
              title="Coming soon — requires document update API"
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
              </svg>
              <span>Edit Details <span className="text-[10px]">· coming soon</span></span>
            </span>

            {/* Delete — disabled */}
            <span
              className="flex w-full items-center gap-2 px-3 py-2 text-xs text-gray-300 cursor-default"
              title="Coming soon — requires document delete API"
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
              </svg>
              <span>Delete <span className="text-[10px]">· coming soon</span></span>
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
