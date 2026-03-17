"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    // Root page always redirects to the Curriculum Library.
    // AppShell handles the org-guard (no org → /organizations).
    router.replace("/library");
  }, [router]);

  return null;
}
