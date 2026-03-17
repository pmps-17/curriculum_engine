"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { getOrgId } from "@/components/OrganizationGate";
import TopNav from "@/components/TopNav";

/**
 * Global layout shell.
 *
 * - Public routes (/login, /api/auth) → render children only.
 * - /organizations → show TopNav + children (no org required).
 * - All other routes → require org selection; redirect to /organizations if none.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useSession();
  const [ready, setReady] = useState(false);

  const isPublic =
    pathname.startsWith("/login") || pathname.startsWith("/api/auth");
  const isOrgPage = pathname.startsWith("/organizations");

  useEffect(() => {
    // Nothing to gate on public or org-picker routes
    if (isPublic || isOrgPage) {
      setReady(true);
      return;
    }
    // Wait for auth to settle
    if (status === "loading") return;

    // If no org selected, bounce to /organizations
    if (!getOrgId()) {
      router.replace("/organizations");
      return;
    }
    setReady(true);
  }, [isPublic, isOrgPage, status, router, pathname]);

  // Public pages: no shell at all
  if (isPublic) return <>{children}</>;

  // While checking auth + org, show nothing (avoids flash)
  if (!ready) return null;

  return (
    <>
      <TopNav />
      {children}
    </>
  );
}
