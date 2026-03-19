"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    // Root page always redirects to Organizations.
    router.replace("/organizations");
  }, [router]);

  return null;
}
