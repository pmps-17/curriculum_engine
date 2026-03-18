"use client";

import { useEffect, useRef, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

export interface OrganizationCardData {
  organization_id: string;
  name: string;
  description?: string | null;
  invite_code?: string | null;
  created_at?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  country_name?: string | null;
  country_code?: string | null;
  state_name?: string | null;
  state_code?: string | null;
  city?: string | null;
}

interface OrganizationCardProps {
  org: OrganizationCardData;
  onSelect: (org: OrganizationCardData) => void;
  onEdit: (org: OrganizationCardData) => void;
  onLeave: (org: OrganizationCardData) => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function OrganizationCard({
  org,
  onSelect,
  onEdit,
  onLeave,
}: OrganizationCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [copied, setCopied] = useState(false);
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

  function handleCopyCode() {
    if (!org.invite_code) return;
    navigator.clipboard.writeText(org.invite_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
    setMenuOpen(false);
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(org)}
      onKeyDown={(e) => { if (e.key === "Enter") onSelect(org); }}
      className="group relative flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition cursor-pointer hover:shadow-md hover:border-gray-300"
    >
      {/* ── 3-dot menu ────────────────────────────────────────────── */}
      <div className="absolute right-3 top-3" ref={menuRef}>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); }}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
          aria-label="Actions"
        >
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z" />
          </svg>
        </button>

        {menuOpen && (
          <div className="absolute right-0 z-50 mt-1 w-44 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
            {/* Edit */}
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setMenuOpen(false); onEdit(org); }}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-gray-700 transition hover:bg-gray-50"
            >
              <svg className="h-3.5 w-3.5 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
              </svg>
              Edit
            </button>

            {/* Copy join code */}
            {org.invite_code && (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); handleCopyCode(); }}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-gray-700 transition hover:bg-gray-50"
              >
                <svg className="h-3.5 w-3.5 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
                </svg>
                {copied ? "Copied!" : "Copy Join Code"}
              </button>
            )}

            {/* Divider */}
            <div className="my-1 border-t border-gray-100" />

            {/* Leave */}
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setMenuOpen(false); onLeave(org); }}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-red-600 transition hover:bg-red-50"
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
              </svg>
              Leave
            </button>
          </div>
        )}
      </div>

      {/* ── Org info ──────────────────────────────────────────────── */}
      <div>
        <h3 className="truncate pr-8 text-[15px] font-semibold text-gray-900">
          {org.name}
        </h3>

        {org.description && (
          <p className="mt-1 line-clamp-2 text-xs text-gray-500">
            {org.description}
          </p>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
          {org.invite_code && (
            <span className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 font-mono text-[11px] text-gray-500">
              <svg className="h-3 w-3 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
              </svg>
              {org.invite_code}
            </span>
          )}
          {org.created_at && (
            <span className="text-[11px] text-gray-400">
              Created {new Date(org.created_at).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
