import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { proxyPaths } from "@/lib/config";
import type { AnalyzeRequest } from "@/lib/schemas";

/* ------------------------------------------------------------------ */
/*  Response type                                                     */
/* ------------------------------------------------------------------ */

export interface AnalyzeResponse {
  analysis_run_id: string;
}

/* ------------------------------------------------------------------ */
/*  Mutation hook                                                     */
/* ------------------------------------------------------------------ */

export function useAnalyzeMutation() {
  return useMutation<AnalyzeResponse, Error, AnalyzeRequest>({
    mutationFn: (data) => {
      // Inject organization_id from localStorage (POC tenancy)
      const orgId =
        typeof window !== "undefined"
          ? localStorage.getItem("organization_id") ?? undefined
          : undefined;

      const payload = {
        ...data,
        ...(orgId ? { organization_id: orgId } : {}),
      };

      return apiFetch<AnalyzeResponse, typeof payload>(proxyPaths.analyze, {
        method: "POST",
        body: payload,
      });
    },
  });
}
