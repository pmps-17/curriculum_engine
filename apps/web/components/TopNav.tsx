"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import Link from "next/link";
import { getOrgId, clearOrg } from "@/lib/orgStore";

/* ------------------------------------------------------------------ */
/*  Nav items                                                         */
/* ------------------------------------------------------------------ */

const NAV_ITEMS = [
  { href: "/organizations", label: "Organizations", requiresOrg: false },
  { href: "/library",       label: "Library",       requiresOrg: true },
  { href: "/compare",       label: "Compare",       requiresOrg: true },
] as const;

/* ------------------------------------------------------------------ */
/*  TopNav                                                            */
/* ------------------------------------------------------------------ */

export default function TopNav() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const email = session?.user?.email ?? "";

  const [hasOrg, setHasOrg] = useState(false);

  useEffect(() => {
    setHasOrg(!!getOrgId());
  }, []);

  // Listen for org changes (e.g. from /organizations page selecting one)
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "organization_name") {
        setHasOrg(!!getOrgId());
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  function handleLogout() {
    clearOrg();
    signOut({ callbackUrl: "/login" });
  }

  function isActive(href: string) {
    if (href === "/organizations") return pathname.startsWith("/organizations");
    if (href === "/library") return pathname === "/" || pathname.startsWith("/library");
    return pathname.startsWith(href);
  }

  return (
    <nav className="sticky top-0 z-40 border-b border-gray-200 bg-white">
      <div className="mx-auto flex h-12 max-w-6xl items-center justify-between px-4 sm:px-6">
        {/* ── Left: logo + links ─────────────────────────────────── */}
        <div className="flex items-center gap-1">
          {/* Logo */}
          <Link
            href="/library"
            className="mr-4 flex items-center gap-1.5 text-sm font-bold text-gray-900"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[#4F46E5] text-[11px] font-black text-white">
              C
            </span>
            <span className="hidden sm:inline">
              Curriculum <span className="text-[#4F46E5]">Engine</span>
            </span>
          </Link>

          {/* Nav links */}
          {NAV_ITEMS.map(({ href, label, requiresOrg }) => {
            const disabled = requiresOrg && !hasOrg;
            const active = isActive(href);

            if (disabled) {
              return (
                <span
                  key={href}
                  className="relative rounded-md px-3 py-1.5 text-[13px] font-medium text-gray-300 cursor-default"
                  title="Select an organization first"
                >
                  {label}
                </span>
              );
            }

            return (
              <Link
                key={href}
                href={href}
                className={`relative rounded-md px-3 py-1.5 text-[13px] font-medium transition ${
                  active
                    ? "text-[#4F46E5]"
                    : "text-gray-500 hover:text-gray-900"
                }`}
              >
                {label}
                {active && (
                  <span className="absolute inset-x-1 -bottom-[9px] h-[2px] rounded-full bg-[#4F46E5]" />
                )}
              </Link>
            );
          })}
        </div>

        {/* ── Right: email + logout ────────────────────────────── */}
        <div className="flex items-center gap-3">
          {/* Email */}
          {email && (
            <span className="hidden text-[11px] text-gray-400 lg:inline">
              {email}
            </span>
          )}

          {/* Logout */}
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-md p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
            title="Log out"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
            </svg>
          </button>
        </div>
      </div>
    </nav>
  );
}
