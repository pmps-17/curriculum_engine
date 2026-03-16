"use client";

import { useEffect, useState, useCallback } from "react";
import { useSession, signOut } from "next-auth/react";
import {
  getWsId,
  getWsName,
  setWsId,
  setWsName,
} from "./WorkspaceGate";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

interface Workspace {
  workspace_id: string;
  name: string;
  invite_code?: string | null;
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function WorkspaceHeader() {
  const { data: session } = useSession();
  const email = session?.user?.email ?? "";
  const [wsName, setWsNameState] = useState("");
  const [open, setOpen] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setWsNameState(getWsName());
  }, []);

  const fetchWorkspaces = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    try {
      const res = await fetch("/api/workspaces");
      if (res.ok) {
        const data: Workspace[] = await res.json();
        setWorkspaces(data);
      }
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, [loading]);

  function handleToggle() {
    const next = !open;
    setOpen(next);
    if (next) fetchWorkspaces();
  }

  function handleSelect(ws: Workspace) {
    setWsId(ws.workspace_id);
    setWsName(ws.name);
    setWsNameState(ws.name);
    setOpen(false);
    window.location.reload(); // simplest way to refresh all state
  }

  function handleLogout() {
    localStorage.removeItem("workspace_id");
    localStorage.removeItem("workspace_name");
    signOut({ callbackUrl: "/login" });
  }

  if (!email) return null;

  return (
    <div className="flex items-center gap-3">
      {/* Workspace selector */}
      <div className="relative">
        <button
          type="button"
          onClick={handleToggle}
          className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-100"
        >
          <span className="inline-block h-2 w-2 rounded-full bg-[#10B981]" />
          <span className="max-w-[140px] truncate">{wsName || "Workspace"}</span>
          <svg className="h-3 w-3 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {open && (
          <div className="absolute right-0 z-50 mt-1 w-56 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
            {loading && (
              <p className="px-3 py-2 text-xs text-gray-400">Loading…</p>
            )}
            {workspaces.map((ws) => (
              <button
                key={ws.workspace_id}
                type="button"
                onClick={() => handleSelect(ws)}
                className={`flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition hover:bg-gray-50 ${
                  ws.workspace_id === getWsId()
                    ? "font-semibold text-[#4F46E5]"
                    : "text-gray-700"
                }`}
              >
                <span className="truncate">{ws.name}</span>
                {ws.invite_code && (
                  <span className="ml-auto shrink-0 rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[10px] text-gray-400">
                    {ws.invite_code}
                  </span>
                )}
              </button>
            ))}
            {!loading && workspaces.length === 0 && (
              <p className="px-3 py-2 text-xs text-gray-400">No workspaces</p>
            )}
          </div>
        )}
      </div>

      {/* Email badge + logout */}
      <span className="hidden text-xs text-gray-400 sm:inline">{email}</span>
      <button
        type="button"
        onClick={handleLogout}
        className="rounded px-2 py-1 text-xs text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
        title="Log out"
      >
        ✕
      </button>
    </div>
  );
}
