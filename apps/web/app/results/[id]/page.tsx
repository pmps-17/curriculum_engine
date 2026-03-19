"use client";

import Link from "next/link";
import { use, useMemo } from "react";
import { useResultsQuery } from "@/features/results/hooks";
import type { AnalysisResults } from "@/features/results/hooks";
import { getOrgId } from "@/lib/orgStore";
import PillarCards from "@/components/PillarCards";
import SkillList from "@/components/SkillList";
import EvidenceAccordion from "@/components/EvidenceAccordion";

/* ------------------------------------------------------------------ */
/*  Skeleton loader                                                   */
/* ------------------------------------------------------------------ */

function Skeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Pillar placeholders */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((n) => (
          <div
            key={n}
            className="h-32 rounded-xl border border-gray-200 bg-gray-100"
          />
        ))}
      </div>
      {/* Skill rows */}
      <div className="space-y-3">
        {[1, 2, 3, 4].map((n) => (
          <div key={n} className="h-10 rounded-lg bg-gray-100" />
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Section wrapper                                                   */
/* ------------------------------------------------------------------ */

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {children}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Results body (extracts flattened skills from nested pillar data)   */
/* ------------------------------------------------------------------ */

function ResultsBody({ data }: { data: AnalysisResults }) {
  // Skills live inside pillar_scores[].skill_scores — flatten them
  const allSkills = useMemo(
    () => (data.pillar_scores ?? []).flatMap((p) => p.skill_scores ?? []),
    [data.pillar_scores],
  );

  return (
    <>
      {/* Pillar scores */}
      <Section title="Pillar Scores">
        <PillarCards pillars={data.pillar_scores ?? []} />
      </Section>

      {/* Skill scores */}
      <Section title="Skill Scores">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <SkillList skills={allSkills} />
        </div>
      </Section>

      {/* Evidence */}
      <Section title="Evidence">
        <EvidenceAccordion
          snippets={data.evidence_snippets ?? []}
          skills={allSkills}
        />
      </Section>

      {/* Findings (optional) */}
      {data.findings && data.findings.length > 0 && (
        <Section title="Findings">
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <ul className="space-y-2">
              {data.findings.map((f, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[#10B981]" />
                  <span>{f.message ?? JSON.stringify(f)}</span>
                </li>
              ))}
            </ul>
          </div>
        </Section>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function ResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, isLoading, isError, error, refetch } = useResultsQuery(id);

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center gap-4 px-6 py-6">
          {/* Browser-back button */}
          <button
            type="button"
            onClick={() => window.history.back()}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700"
            aria-label="Go back"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-bold tracking-tight text-gray-900">
              Analysis <span className="text-[#4F46E5]">Results</span>
            </h1>
            <p className="truncate text-xs text-gray-400 font-mono">{id}</p>
          </div>

          {/* Contextual quick-links */}
          <div className="hidden items-center gap-2 sm:flex">
            <Link
              href={`/library?organization_id=${getOrgId()}`}
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:border-[#4F46E5]/30 hover:text-[#4F46E5]"
            >
              ← Library
            </Link>
            <Link
              href="/compare"
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:border-[#4F46E5]/30 hover:text-[#4F46E5]"
            >
              Compare
            </Link>
          </div>
        </div>
      </header>

      {/* Body */}
      <div className="mx-auto max-w-4xl px-6 py-10 space-y-10">
        {/* Loading */}
        {isLoading && <Skeleton />}

        {/* Error */}
        {isError && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center space-y-3">
            <p className="text-sm text-red-600">
              {error?.message ?? "Failed to load results."}
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

        {/* Success */}
        {data && (
          <ResultsBody data={data} />
        )}
      </div>
    </main>
  );
}
