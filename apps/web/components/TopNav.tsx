"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import Link from "next/link";
import { getOrgId, getOrgName } from "@/components/OrganizationGate";

/* ------------------------------------------------------------------ */
/*  Nav items                                                         */
/* ------------------------------------------------------------------ */

const NAV_ITEMS = [
  { href: "/library",       label: "Library" },
  { href: "/compare",       label: "Compare" },
] as const;

/* ------------------------------------------------------------------ */
/*  TopNav                                                            */
/* ------------------------------------------------------------------ */

export default function TopNav() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const email = session?.user?.email ?? "";

  const [orgName, setOrgName] = useState("");

  useEffect(() => {
    setOrgName(getOrgName());
  }, []);

  // Listen for org changes (e.g. from /organizations page selecting one)
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "organization_name") setOrgName(e.newValue ?? "");
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  function handleLogout() {
    localStorage.removeItem("organization_id");
    localStorage.removeItem("organization_name");
    signOut({ callbackUrl: "/login" });
  }

  function isActive(href: string) {
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
          {NAV_ITEMS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`relative rounded-md px-3 py-1.5 text-[13px] font-medium transition ${
                isActive(href)
                  ? "text-[#4F46E5]"
                  : "text-gray-500 hover:text-gray-900"
              }`}
            >
              {label}
              {isActive(href) && (
                <span className="absolute inset-x-1 -bottom-[9px] h-[2px] rounded-full bg-[#4F46E5]" />
              )}
            </Link>
          ))}
        </div>

        {/* ── Right: org pill + email + logout ────────────────────── */}
        <div className="flex items-center gap-3">
          {/* Org context pill */}
          {orgName && (
            <Link
              href="/organizations"
              className="flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-[11px] text-gray-600 transition hover:border-[#4F46E5]/30 hover:bg-[#4F46E5]/5"
              title="Switch organization"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-[#10B981]" />
              <span className="max-w-[120px] truncate font-medium">{orgName}</span>
              <svg className="h-3 w-3 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 15L12 18.75 15.75 15m-7.5-6L12 5.25 15.75 9" />
              </svg>
            </Link>
          )}

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
