"use client";

import { usePathname } from "next/navigation";
import OrganizationGate from "@/components/OrganizationGate";
import OrganizationHeader from "@/components/OrganizationHeader";

/**
 * Wraps all page content. Shows the nav bar + organization gate on
 * authenticated routes, and renders children directly on public
 * routes like /login.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublic = pathname.startsWith("/login");

  if (isPublic) {
    return <>{children}</>;
  }

  return (
    <>
      {/* Global nav bar */}
      <nav className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
        <div className="flex items-center gap-6">
          <a href="/" className="text-sm font-bold text-gray-900">
            Curriculum <span className="text-[#4F46E5]">Engine</span>
          </a>
          <a href="/compare" className="text-sm text-gray-500 transition hover:text-[#4F46E5]">
            Compare
          </a>
        </div>
        <OrganizationHeader />
      </nav>
      <OrganizationGate>
        {children}
      </OrganizationGate>
    </>
  );
}
