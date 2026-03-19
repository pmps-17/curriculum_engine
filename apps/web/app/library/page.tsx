"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { listDocuments, type DocumentLibraryItem as LibraryItem } from "@/lib/documents";
import type { OrganizationCardData } from "@/components/OrganizationCard";
import DocumentLibraryTable from "@/components/DocumentLibraryTable";

/* ------------------------------------------------------------------ */
/*  Skeleton loader                                                   */
/* ------------------------------------------------------------------ */

function Skeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {[1, 2, 3, 4].map((n) => (
        <div
          key={n}
          className="h-12 rounded-lg border border-gray-200 bg-gray-100"
        />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function LibraryPage() {
  const searchParams = useSearchParams();
  const orgId = searchParams.get("organization_id") ?? "";

  const [org, setOrg] = useState<OrganizationCardData | null>(null);
  const [docs, setDocs] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /* ── Fetch org details (lightweight — reuses list endpoint) ──── */

  useEffect(() => {
    if (!orgId) return;
    fetch("/api/organizations")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((orgs: OrganizationCardData[]) => {
        setOrg(orgs.find((o) => o.organization_id === orgId) ?? null);
      })
      .catch(() => {}); // non-fatal — header just won't show extras
  }, [orgId]);

  const orgName = org?.name ?? "";

  /* ── Fetch documents ─────────────────────────────────────────── */

  const fetchDocs = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    setError("");
    try {
      setDocs(await listDocuments(orgId));
    } catch {
      setError("Failed to load documents.");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  /* ── Render ──────────────────────────────────────────────────── */

  return (
    <main className="min-h-screen bg-gray-50">
      {/* ── Header ──────────────────────────────────────────────── */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-[1000px] items-center justify-between px-6 py-6">
          <div className="min-w-0">
            <h1 className="text-xl font-bold tracking-tight text-gray-900">
              Curriculum <span className="text-[#4F46E5]">Library</span>
            </h1>
            {orgName && (
              <p className="mt-0.5 text-sm font-medium text-gray-600">{orgName}</p>
            )}
            {org?.description && (
              <p className="mt-0.5 text-xs text-gray-400 line-clamp-2">
                {org.description}
              </p>
            )}
            {(org?.contact_name || org?.contact_email) && (
              <p className="mt-0.5 text-xs text-gray-400">
                Contact:{" "}
                {[org.contact_name, org.contact_email]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            )}
          </div>

          <Link
            href={`/library/upload?organization_id=${orgId}`}
            className="inline-flex items-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA]"
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
                d="M12 16V4m0 0l-4 4m4-4l4 4M4 20h16"
              />
            </svg>
            Upload &amp; Analyze
          </Link>
        </div>
      </header>

      {/* ── Body ──────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-[1000px] px-6 py-8">
        {loading && <Skeleton />}

        {!loading && error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center space-y-3">
            <p className="text-sm text-red-600">{error}</p>
            <button
              type="button"
              onClick={fetchDocs}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-[#4338CA]"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && (
          <DocumentLibraryTable
            items={docs}
            organizationId={orgId}
            onMutated={fetchDocs}
          />
        )}
      </div>
    </main>
  );
}
