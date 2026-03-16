"use client";

import { useState, useMemo } from "react";
import type { EvidenceSnippet, SkillScore } from "@/features/results/hooks";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const INITIAL_SHOW = 3;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Group snippets by skill_code (or skill_id) */
function groupBySkill(snippets: EvidenceSnippet[]): Map<string, EvidenceSnippet[]> {
  const map = new Map<string, EvidenceSnippet[]>();
  for (const s of snippets) {
    const key = s.skill_code ?? s.skill_id ?? "unknown";
    const arr = map.get(key) ?? [];
    arr.push(s);
    map.set(key, arr);
  }
  return map;
}

function skillLabel(key: string, skills: SkillScore[], snippets: EvidenceSnippet[]): string {
  // Try skill scores first
  const match = skills.find((s) => s.skill_code === key || s.skill_id === key);
  if (match?.skill_name) return `${match.skill_name}${match.skill_code ? ` (${match.skill_code})` : ""}`;
  // Fallback: try the evidence snippet itself (has skill_name since API v2)
  const ev = snippets.find((s) => s.skill_code === key || s.skill_id === key);
  if (ev?.skill_name) return `${ev.skill_name}${ev.skill_code ? ` (${ev.skill_code})` : ""}`;
  return key;
}

/* ------------------------------------------------------------------ */
/*  Sub-component: single accordion group                             */
/* ------------------------------------------------------------------ */

function SkillGroup({
  skillKey,
  label,
  snippets,
}: {
  skillKey: string;
  label: string;
  snippets: EvidenceSnippet[];
}) {
  const [open, setOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const visible = showAll ? snippets : snippets.slice(0, INITIAL_SHOW);
  const hasMore = snippets.length > INITIAL_SHOW;

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {/* Header */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm font-medium text-gray-800 transition hover:bg-gray-50"
      >
        <span className="truncate">{label}</span>
        <span className="flex items-center gap-2 shrink-0">
          <span className="rounded-full bg-[#4F46E5]/10 px-2 py-0.5 text-[11px] font-semibold text-[#4F46E5]">
            {snippets.length}
          </span>
          <svg
            className={`h-4 w-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </button>

      {/* Body */}
      {open && (
        <div className="border-t border-gray-100 px-4 py-3 space-y-3">
          {visible.map((ev, i) => (
            <div
              key={`${skillKey}-${i}`}
              className="rounded-md bg-gray-50 px-3.5 py-3 text-sm space-y-1.5"
            >
              {/* Snippet text */}
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                {ev.snippet_text ?? "—"}
              </p>

              {/* Meta pills */}
              <div className="flex flex-wrap gap-2 pt-1">
                {ev.section_type && (
                  <span className="rounded bg-gray-200/70 px-2 py-0.5 text-[11px] font-medium text-gray-600">
                    {ev.section_type}
                  </span>
                )}
                {ev.reason_type && (
                  <span className="rounded bg-[#10B981]/10 px-2 py-0.5 text-[11px] font-medium text-[#10B981]">
                    {ev.reason_type}
                  </span>
                )}
                {ev.contribution_score != null && (
                  <span className="rounded bg-[#4F46E5]/10 px-2 py-0.5 text-[11px] font-medium text-[#4F46E5]">
                    contrib {Math.round(ev.contribution_score * 100)}%
                  </span>
                )}
              </div>
            </div>
          ))}

          {/* Show more / less */}
          {hasMore && (
            <button
              type="button"
              onClick={() => setShowAll((v) => !v)}
              className="text-xs font-medium text-[#4F46E5] hover:underline"
            >
              {showAll
                ? "Show less"
                : `Show ${snippets.length - INITIAL_SHOW} more`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                    */
/* ------------------------------------------------------------------ */

interface Props {
  snippets: EvidenceSnippet[];
  skills: SkillScore[];
}

export default function EvidenceAccordion({ snippets, skills }: Props) {
  const grouped = useMemo(() => groupBySkill(snippets), [snippets]);

  if (snippets.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">No evidence snippets available.</p>
    );
  }

  return (
    <div className="space-y-2">
      {[...grouped.entries()].map(([key, items]) => (
        <SkillGroup
          key={key}
          skillKey={key}
          label={skillLabel(key, skills, snippets)}
          snippets={items}
        />
      ))}
    </div>
  );
}
