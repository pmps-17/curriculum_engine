"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getOrgId } from "@/lib/orgStore";
import { proxyPaths } from "@/lib/config";
import type { CurriculumSetData } from "@/components/CurriculumSetCard";
import AnalyzeForm from "@/components/AnalyzeForm";

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function CurriculumSetDetailPage() {
  const params = useParams<{ setId: string }>();
  const orgId = getOrgId();

  const [set, setSet] = useState<CurriculumSetData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /* ── Fetch the set (from the list endpoint, filter client-side) ── */

  const fetchSet = useCallback(async () => {
    if (!orgId || !params.setId) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${proxyPaths.curriculumSets}?organization_id=${orgId}`);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data: CurriculumSetData[] = await res.json();
      const found = data.find((s) => s.id === params.setId);
      if (!found) throw new Error("Curriculum set not found.");
      setSet(found);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [orgId, params.setId]);

  useEffect(() => {
    fetchSet();
  }, [fetchSet]);

  /* ── No org guard ────────────────────────────────────────────────── */

  if (!orgId) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="mx-auto flex max-w-[800px] flex-col items-center justify-center px-6 py-24 text-center">
          <p className="text-sm text-gray-500">No organization selected.</p>
          <Link href="/organizations" className="mt-4 text-sm font-medium text-[#4F46E5] hover:underline">
            Go to Organizations →
          </Link>
        </div>
      </main>
    );
  }

  /* ── Loading ─────────────────────────────────────────────────────── */

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="mx-auto max-w-[800px] px-6 py-10 animate-pulse">
          <div className="h-6 w-48 rounded bg-gray-200" />
          <div className="mt-2 h-4 w-32 rounded bg-gray-100" />
          <div className="mt-8 h-40 rounded-xl border border-gray-200 bg-gray-100" />
        </div>
      </main>
    );
  }

  /* ── Error ───────────────────────────────────────────────────────── */

  if (error || !set) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="mx-auto max-w-[800px] px-6 py-10">
          <Link
            href="/library"
            className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-[#4F46E5] transition"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Back to Library
          </Link>
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-sm text-red-600">{error || "Curriculum set not found."}</p>
          </div>
        </div>
      </main>
    );
  }

  /* ── Render ──────────────────────────────────────────────────────── */

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-[800px] px-6 py-6">
          {/* Back link */}
          <Link
            href="/library"
            className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-[#4F46E5] transition"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Library
          </Link>

          {/* Title */}
          <h1 className="mt-2 text-xl font-bold tracking-tight text-gray-900">
            {set.title}
          </h1>

          {/* Meta chips */}
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {set.subject && (
              <span className="inline-flex items-center gap-1 rounded-full bg-[#4F46E5]/5 px-2.5 py-0.5 text-[11px] font-medium text-[#4F46E5]">
                <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
                {set.subject}
              </span>
            )}
            {set.grade_band && (
              <span className="inline-flex items-center gap-1 rounded-full bg-[#10B981]/5 px-2.5 py-0.5 text-[11px] font-medium text-[#10B981]">
                <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.636 50.636 0 00-2.658-.813A59.906 59.906 0 0112 3.493a59.903 59.903 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0112 13.489a50.702 50.702 0 017.74-3.342" />
                </svg>
                Grades {set.grade_band}
              </span>
            )}
            <span className="text-[11px] text-gray-400">
              Created {new Date(set.created_at).toLocaleDateString()}
            </span>
          </div>

          {/* Description */}
          {set.description && (
            <p className="mt-3 text-sm text-gray-500">
              {set.description}
            </p>
          )}
        </div>
      </header>

      {/* Body — Upload & Analyze form, scoped to this set */}
      <div className="mx-auto max-w-[800px] px-6 py-8">
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
          <h2 className="mb-1 text-base font-semibold text-gray-900">
            Upload &amp; Analyze
          </h2>
          <p className="mb-5 text-sm text-gray-500">
            Submit curriculum content for this set. Uploads and analysis runs will be automatically linked.
          </p>
          <AnalyzeForm
            curriculumSetId={set.id}
            curriculumSetName={set.title}
            onSuccess={() => fetchSet()}
          />
        </div>
      </div>
    </main>
  );
}
