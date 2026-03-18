"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getOrgId, getOrgName } from "@/lib/orgStore";
import { proxyPaths } from "@/lib/config";
import CurriculumSetCard from "@/components/CurriculumSetCard";
import type { CurriculumSetData } from "@/components/CurriculumSetCard";
import CreateCurriculumSetModal from "@/components/CreateCurriculumSetModal";

/* ------------------------------------------------------------------ */
/*  Skeleton loader                                                   */
/* ------------------------------------------------------------------ */

function Skeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 animate-pulse">
      {[1, 2, 3, 4, 5, 6].map((n) => (
        <div
          key={n}
          className="h-[160px] rounded-xl border border-gray-200 bg-gray-100"
        />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  No-org guard                                                      */
/* ------------------------------------------------------------------ */

function NoOrgSelected() {
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="mx-auto flex max-w-[1000px] flex-col items-center justify-center px-6 py-24 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#4F46E5]/10">
          <svg className="h-8 w-8 text-[#4F46E5]" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3.75h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008z" />
          </svg>
        </div>
        <h2 className="mt-5 text-lg font-semibold text-gray-900">
          No organization selected
        </h2>
        <p className="mt-1.5 max-w-sm text-sm text-gray-500">
          Select an organization first to view your curriculum sets.
        </p>
        <Link
          href="/organizations"
          className="mt-6 inline-flex items-center gap-2 rounded-lg bg-[#4F46E5] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA]"
        >
          Go to Organizations
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
        </Link>
      </div>
    </main>
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
        Create a curriculum set to start organizing and analyzing your curriculum.
      </p>
      <button
        type="button"
        onClick={onAdd}
        className="mt-5 inline-flex items-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA]"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Create Curriculum Set
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function LibraryPage() {
  const orgId = getOrgId();
  const orgName = getOrgName();
  const router = useRouter();

  const [sets, setSets] = useState<CurriculumSetData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  /* ── Fetch curriculum sets ───────────────────────────────────────── */

  const fetchSets = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${proxyPaths.curriculumSets}?organization_id=${orgId}`);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data: CurriculumSetData[] = await res.json();
      setSets(data);
    } catch {
      setError("Failed to load curriculum sets.");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    fetchSets();
  }, [fetchSets]);

  /* ── Guards ──────────────────────────────────────────────────────── */

  if (!orgId) return <NoOrgSelected />;

  /* ── Handlers ────────────────────────────────────────────────────── */

  function handleCardClick(set: CurriculumSetData) {
    router.push(`/library/${set.id}`);
  }

  function handleCreated() {
    fetchSets();
  }

  /* ── Render ──────────────────────────────────────────────────────── */

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-[1000px] items-center justify-between px-6 py-6">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-gray-900">
              Curriculum <span className="text-[#4F46E5]">Library</span>
            </h1>
            {orgName && (
              <p className="mt-0.5 text-xs text-gray-400">
                {orgName}
              </p>
            )}
          </div>

          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA]"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Set
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="mx-auto max-w-[1000px] px-6 py-8">
        {/* Loading */}
        {loading && <Skeleton />}

        {/* Error */}
        {!loading && error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center space-y-3">
            <p className="text-sm text-red-600">{error}</p>
            <button
              type="button"
              onClick={fetchSets}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-[#4338CA]"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && sets.length === 0 && (
          <EmptyState onAdd={() => setCreateOpen(true)} />
        )}

        {/* Grid */}
        {!loading && !error && sets.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sets.map((s) => (
              <CurriculumSetCard
                key={s.id}
                set={s}
                onClick={handleCardClick}
              />
            ))}
          </div>
        )}
      </div>

      {/* Create modal */}
      <CreateCurriculumSetModal
        open={createOpen}
        organizationId={orgId}
        onClose={() => setCreateOpen(false)}
        onCreated={handleCreated}
      />
    </main>
  );
}
