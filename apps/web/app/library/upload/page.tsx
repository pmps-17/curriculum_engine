"use client";

import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getOrgName } from "@/lib/orgStore";
import AnalyzeForm from "@/components/AnalyzeForm";

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function UploadPage() {
  const searchParams = useSearchParams();
  const orgId = searchParams.get("organization_id") ?? "";
  const router = useRouter();
  const orgName = getOrgName();

  return (
    <main className="min-h-screen bg-gray-50">
      {/* ── Header ──────────────────────────────────────────────── */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-[720px] items-center justify-between px-6 py-6">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-gray-900">
              Upload &amp; <span className="text-[#4F46E5]">Analyze</span>
            </h1>
            {orgName && (
              <p className="mt-0.5 text-xs text-gray-400">{orgName}</p>
            )}
          </div>

          <Link
            href={`/library?organization_id=${orgId}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3.5 py-2 text-sm font-medium text-gray-600 shadow-sm transition hover:border-gray-300 hover:text-gray-900"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"
              />
            </svg>
            Library
          </Link>
        </div>
      </header>

      {/* ── Body ──────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-[720px] px-6 py-8">
        <AnalyzeForm
          organizationId={orgId}
          onSuccess={() => router.push(`/library?organization_id=${orgId}`)}
        />
      </div>
    </main>
  );
}
