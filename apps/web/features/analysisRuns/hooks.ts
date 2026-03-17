import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

/** Mirrors the backend AnalysisRunSummary schema. */
export interface AnalysisRunItem {
  analysis_run_id: string;
  title: string | null;
  subject: string | null;
  grade_band: string | null;
  status: string;
  created_at: string;
  document_id: string | null;
}

/* ------------------------------------------------------------------ */
/*  Hook                                                              */
/* ------------------------------------------------------------------ */

/**
 * Fetch the list of analysis runs for an organization.
 *
 * Calls `GET /api/analysis-runs?organization_id=...&limit=50`
 * (Next.js proxy → FastAPI backend).
 *
 * X-User-Email is automatically injected by `apiFetch`.
 */
export function useAnalysisRunsQuery(organizationId: string) {
  return useQuery<AnalysisRunItem[], Error>({
    queryKey: ["analysis-runs", organizationId],
    queryFn: () =>
      apiFetch<AnalysisRunItem[]>(
        `/api/analysis-runs?organization_id=${encodeURIComponent(organizationId)}&limit=50`,
        { method: "GET" },
      ),
    enabled: !!organizationId,
    staleTime: 30_000,
    retry: 1,
  });
}
