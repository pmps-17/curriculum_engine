import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { OrganizationCardData } from "@/components/OrganizationCard";

/* ------------------------------------------------------------------ */
/*  Hook                                                              */
/* ------------------------------------------------------------------ */

/**
 * Fetch full details for a single organization.
 *
 * Calls `GET /api/organizations` (Next.js proxy → FastAPI list endpoint)
 * and plucks the matching org by ID.  TanStack Query caches the list so
 * repeated renders / navigations don't re-fetch unnecessarily.
 */
export function useOrganizationDetail(orgId: string) {
  return useQuery<OrganizationCardData | null, Error>({
    queryKey: ["organization-detail", orgId],
    queryFn: async () => {
      const orgs = await apiFetch<OrganizationCardData[]>("/api/organizations", {
        method: "GET",
      });
      return orgs.find((o) => o.organization_id === orgId) ?? null;
    },
    enabled: !!orgId,
    staleTime: 60_000,
    retry: 1,
  });
}
