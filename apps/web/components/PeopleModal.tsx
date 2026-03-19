"use client";

import { useEffect, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

interface Member {
  user_id: string;
  email: string;
  name: string | null;
  role: "admin" | "member";
  joined_at: string;
}

interface PeopleModalProps {
  open: boolean;
  organizationId: string;
  organizationName: string;
  onClose: () => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function PeopleModal({
  open,
  organizationId,
  organizationName,
  onClose,
}: PeopleModalProps) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !organizationId) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(`/api/organizations/${organizationId}/members`);
        if (!res.ok) throw new Error(`Error ${res.status}`);
        const data: Member[] = await res.json();
        if (!cancelled) setMembers(data);
      } catch {
        if (!cancelled) setError("Failed to load members.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [open, organizationId]);

  if (!open) return null;

  function handleBackdrop(e: React.MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
      onClick={handleBackdrop}
    >
      <div className="w-full max-w-md rounded-2xl border border-gray-200/80 bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <div>
            <h3 className="text-base font-semibold text-gray-900">People</h3>
            <p className="mt-0.5 text-xs text-gray-500">{organizationName}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="max-h-80 overflow-y-auto px-6 py-4">
          {loading && (
            <div className="space-y-3 animate-pulse">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-full bg-gray-200" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-3 w-32 rounded bg-gray-200" />
                    <div className="h-2.5 w-20 rounded bg-gray-100" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {!loading && error && (
            <p className="text-center text-sm text-red-500">{error}</p>
          )}

          {!loading && !error && members.length === 0 && (
            <p className="text-center text-sm text-gray-400">No members found.</p>
          )}

          {!loading && !error && members.length > 0 && (
            <ul className="divide-y divide-gray-100">
              {members.map((m) => (
                <li key={m.user_id} className="flex items-center gap-3 py-2.5">
                  {/* Avatar */}
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#4F46E5]/10 text-xs font-semibold text-[#4F46E5]">
                    {(m.name ?? m.email).charAt(0).toUpperCase()}
                  </div>

                  {/* Info */}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900">
                      {m.name ?? m.email}
                    </p>
                    {m.name && (
                      <p className="truncate text-xs text-gray-400">{m.email}</p>
                    )}
                  </div>

                  {/* Role badge */}
                  {m.role === "admin" ? (
                    <span className="shrink-0 rounded-full bg-[#4F46E5]/10 px-2 py-0.5 text-[10px] font-semibold text-[#4F46E5]">
                      Admin
                    </span>
                  ) : (
                    <span className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500">
                      Member
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
