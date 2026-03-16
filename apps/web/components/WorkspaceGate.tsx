"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { usePathname } from "next/navigation";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

interface Workspace {
  workspace_id: string;
  name: string;
  invite_code?: string | null;
  created_at?: string;
}

/* ------------------------------------------------------------------ */
/*  localStorage helpers (workspace only — email comes from session)  */
/* ------------------------------------------------------------------ */

function getWsId(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("workspace_id") ?? "";
}
function setWsId(v: string) {
  localStorage.setItem("workspace_id", v);
}
function getWsName(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("workspace_name") ?? "";
}
function setWsName(v: string) {
  localStorage.setItem("workspace_name", v);
}

export { getWsId, getWsName, setWsId, setWsName };

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function WorkspaceGate({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { data: session, status } = useSession();
  const [ready, setReady] = useState(false);
  const [wsId, setWsIdState] = useState("");

  // Hydrate workspace from localStorage after mount
  useEffect(() => {
    setWsIdState(getWsId());
    setReady(true);
  }, []);

  const handleDone = useCallback(() => {
    setWsIdState(getWsId());
  }, []);

  // Public routes bypass the gate entirely
  if (pathname.startsWith("/login") || pathname.startsWith("/api/auth")) {
    return <>{children}</>;
  }

  // While NextAuth session is loading or localStorage hasn't hydrated
  if (status === "loading" || !ready) return null;

  // If no session somehow (middleware should redirect, but defensive)
  if (!session?.user?.email) return null;

  // Gate: show workspace onboarding if no workspace selected
  if (!wsId) {
    return (
      <OnboardingScreen
        email={session.user.email}
        onDone={handleDone}
      />
    );
  }

  return <>{children}</>;
}

/* ------------------------------------------------------------------ */
/*  Onboarding screen (workspace only — no email step)                */
/* ------------------------------------------------------------------ */

function OnboardingScreen({
  email,
  onDone,
}: {
  email: string;
  onDone: () => void;
}) {
  const [mode, setMode] = useState<"create" | "join">("create");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canSubmit =
    mode === "create" ? name.trim().length > 0 : code.trim().length > 0;

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Enter a workspace name.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/workspaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim() }),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => null);
        throw new Error(b?.detail ?? `Error ${res.status}`);
      }
      const ws: Workspace = await res.json();
      setWsId(ws.workspace_id);
      setWsName(ws.name);
      onDone();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create workspace.");
    } finally {
      setLoading(false);
    }
  }

  async function handleJoin(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim()) {
      setError("Enter the invite code.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/workspaces/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invite_code: code.trim().toUpperCase() }),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => null);
        throw new Error(b?.detail ?? `Error ${res.status}`);
      }
      const ws: Workspace = await res.json();
      setWsId(ws.workspace_id);
      setWsName(ws.name);
      onDone();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid invite code.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-53px)] items-center justify-center bg-[#F8FAFC] px-4 py-12">
      <div className="w-full max-w-[560px] rounded-2xl border border-gray-200/80 bg-white p-7 shadow-[0_4px_24px_rgba(0,0,0,0.05)]">
        {/* ── Header ─────────────────────────────────────────────── */}
        <div className="text-center">
          <h1 className="text-[22px] font-bold tracking-tight text-gray-900">
            Curriculum <span className="text-[#4F46E5]">Engine</span>
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Create or join a workspace to get started.
          </p>
        </div>

        {/* ── Identity pill ──────────────────────────────────────── */}
        <div className="mt-4 flex justify-center">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-3.5 py-1 text-xs text-gray-500">
            <span className="h-1.5 w-1.5 rounded-full bg-[#10B981]" />
            Signed in as{" "}
            <span className="font-medium text-gray-700">{email}</span>
          </span>
        </div>

        {/* ── Segmented toggle ───────────────────────────────────── */}
        <div className="mx-auto mt-6 flex max-w-[320px] rounded-lg bg-gray-100 p-1">
          {(["create", "join"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => {
                setMode(m);
                setError("");
              }}
              className={`flex-1 rounded-md py-2 text-[13px] font-semibold transition-all ${
                mode === m
                  ? "bg-[#4F46E5] text-white shadow-sm"
                  : "bg-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {m === "create" ? "Create" : "Join"}
            </button>
          ))}
        </div>

        {/* ── Form ───────────────────────────────────────────────── */}
        {mode === "create" ? (
          <form onSubmit={handleCreate} className="mt-6 space-y-5">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700">
                Workspace Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setError("");
                }}
                placeholder="e.g., Greenfield Academy"
                className="h-11 rounded-lg border border-gray-200 bg-white px-3.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20"
                autoFocus
              />
            </div>

            {error && (
              <p className="text-xs text-red-500">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading || !canSubmit}
              className="flex h-11 w-full items-center justify-center rounded-lg bg-[#4F46E5] text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Creating…
                </span>
              ) : (
                "Create Workspace"
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleJoin} className="mt-6 space-y-5">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700">
                Invite Code
              </label>
              <input
                type="text"
                value={code}
                onChange={(e) => {
                  setCode(e.target.value.toUpperCase());
                  setError("");
                }}
                placeholder="e.g., 8F3KQ2"
                maxLength={12}
                className="h-11 rounded-lg border border-gray-200 bg-white px-3.5 text-sm font-mono tracking-widest shadow-sm outline-none transition placeholder:font-sans placeholder:tracking-normal placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20"
                autoFocus
              />
              <p className="text-xs text-gray-400">
                Ask the workspace owner for the invite code.
              </p>
            </div>

            {error && (
              <p className="text-xs text-red-500">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading || !canSubmit}
              className="flex h-11 w-full items-center justify-center rounded-lg bg-[#4F46E5] text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Joining…
                </span>
              ) : (
                "Join Workspace"
              )}
            </button>
          </form>
        )}

        {/* ── Microcopy ──────────────────────────────────────────── */}
        <p className="mt-5 text-center text-[11px] text-gray-400">
          Workspaces keep your analyses organized and private.
        </p>
      </div>
    </div>
  );
}
