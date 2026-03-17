"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  getOrgId,
  setOrgId,
  setOrgName,
} from "@/components/OrganizationGate";
import OrganizationCard from "@/components/OrganizationCard";
import CreateOrganizationModal from "@/components/CreateOrganizationModal";
import JoinOrganizationModal from "@/components/JoinOrganizationModal";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

interface Organization {
  organization_id: string;
  name: string;
  invite_code?: string | null;
  created_at?: string | null;
}

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function OrganizationsPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const email = session?.user?.email ?? "";

  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [showJoin, setShowJoin] = useState(false);

  /* ── Fetch orgs ──────────────────────────────────────────────────── */
  const fetchOrganizations = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/organizations");
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data: Organization[] = await res.json();
      setOrganizations(data);
    } catch {
      setError("Failed to load organizations.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  /* ── Select & navigate ───────────────────────────────────────────── */
  function selectOrg(org: { organization_id: string; name: string }) {
    setOrgId(org.organization_id);
    setOrgName(org.name);
    router.push("/");
  }

  /* ── Created / Joined handlers ───────────────────────────────────── */
  function handleCreated(org: { organization_id: string; name: string }) {
    setShowCreate(false);
    selectOrg(org);
  }

  function handleJoined(org: { organization_id: string; name: string }) {
    setShowJoin(false);
    selectOrg(org);
  }

  /* ── Current org id for highlighting ─────────────────────────────── */
  const activeOrgId = typeof window !== "undefined" ? getOrgId() : "";

  /* ── Render ──────────────────────────────────────────────────────── */
  return (
    <main className="min-h-[calc(100vh-53px)] bg-[#F8FAFC]">
      <div className="mx-auto max-w-4xl px-6 py-10">
        {/* ── Page header ──────────────────────────────────────────── */}
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">
              My Organizations
            </h1>
            {email && (
              <p className="mt-0.5 text-sm text-gray-500">
                Manage your organizations and analyses
              </p>
            )}
          </div>
          <div className="mt-3 flex items-center gap-2 sm:mt-0">
            <button
              type="button"
              onClick={() => setShowJoin(true)}
              className="flex h-9 items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-4 text-sm font-medium text-gray-700 shadow-sm transition hover:border-[#4F46E5] hover:text-[#4F46E5]"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM3 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 019.374 21c-2.331 0-4.512-.645-6.374-1.766z" />
              </svg>
              Join
            </button>
            <button
              type="button"
              onClick={() => setShowCreate(true)}
              className="flex h-9 items-center gap-1.5 rounded-lg bg-[#4F46E5] px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA]"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Create
            </button>
          </div>
        </div>

        {/* ── Loading skeleton ─────────────────────────────────────── */}
        {loading && (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-[140px] animate-pulse rounded-xl border border-gray-200 bg-white"
              />
            ))}
          </div>
        )}

        {/* ── Error ────────────────────────────────────────────────── */}
        {!loading && error && (
          <div className="mt-8 rounded-xl border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-sm text-red-600">{error}</p>
            <button
              type="button"
              onClick={fetchOrganizations}
              className="mt-3 text-sm font-medium text-[#4F46E5] hover:underline"
            >
              Try again
            </button>
          </div>
        )}

        {/* ── Empty state ──────────────────────────────────────────── */}
        {!loading && !error && organizations.length === 0 && (
          <div className="mt-12 flex flex-col items-center text-center">
            {/* Icon */}
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#4F46E5]/10">
              <svg className="h-8 w-8 text-[#4F46E5]" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3.75h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008z" />
              </svg>
            </div>

            <h2 className="mt-5 text-lg font-semibold text-gray-900">
              No organizations yet
            </h2>
            <p className="mt-1.5 max-w-sm text-sm text-gray-500">
              Create an organization to start analyzing curriculum, or join an existing one with an invite code.
            </p>

            <div className="mt-6 flex items-center gap-3">
              <button
                type="button"
                onClick={() => setShowCreate(true)}
                className="flex h-10 items-center gap-1.5 rounded-lg bg-[#4F46E5] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA]"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Create Organization
              </button>
              <button
                type="button"
                onClick={() => setShowJoin(true)}
                className="flex h-10 items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-5 text-sm font-medium text-gray-700 shadow-sm transition hover:border-[#4F46E5] hover:text-[#4F46E5]"
              >
                Join with Code
              </button>
            </div>
          </div>
        )}

        {/* ── Org cards grid ───────────────────────────────────────── */}
        {!loading && !error && organizations.length > 0 && (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {organizations.map((org) => (
              <OrganizationCard
                key={org.organization_id}
                name={org.name}
                organizationId={org.organization_id}
                inviteCode={org.invite_code}
                createdAt={org.created_at}
                isActive={org.organization_id === activeOrgId}
                onOpen={() => selectOrg(org)}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Modals ─────────────────────────────────────────────────── */}
      <CreateOrganizationModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={handleCreated}
      />
      <JoinOrganizationModal
        open={showJoin}
        onClose={() => setShowJoin(false)}
        onJoined={handleJoined}
      />
    </main>
  );
}
