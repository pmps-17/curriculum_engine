import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { proxyPaths } from "@/lib/config";

/* ------------------------------------------------------------------ */
/*  Response types (defensive – every nested field is optional)        */
/* ------------------------------------------------------------------ */

export interface PillarScore {
  pillar_code?: string;
  pillar_name?: string;
  pillar_description?: string;
  score?: number;
  confidence?: number;
  skill_scores?: SkillScore[];
}

export interface SkillScore {
  skill_code?: string;
  skill_id?: string;
  skill_name?: string;
  score?: number;
  confidence?: number;
  taught_flag?: boolean;
  assessed_flag?: boolean;
}

export interface EvidenceSnippet {
  skill_code?: string;
  skill_id?: string;
  skill_name?: string;
  snippet_text?: string;
  relevance_score?: number;
  section_type?: string;
  reason_type?: string;
  contribution_score?: number;
}

export interface Finding {
  type?: string;
  message?: string;
  [key: string]: unknown;
}

export interface AnalysisResults {
  analysis_run_id?: string;
  pillar_scores?: PillarScore[];
  skill_scores?: SkillScore[];
  evidence_snippets?: EvidenceSnippet[];
  findings?: Finding[];
  [key: string]: unknown;
}

/* ------------------------------------------------------------------ */
/*  Query hook                                                        */
/* ------------------------------------------------------------------ */

export function useResultsQuery(analysisRunId: string) {
  return useQuery<AnalysisResults, Error>({
    queryKey: ["results", analysisRunId],
    queryFn: () =>
      apiFetch<AnalysisResults>(proxyPaths.results(analysisRunId), {
        method: "GET",
        // X-User-Email is automatically injected by apiFetch
      }),
    enabled: !!analysisRunId,
    retry: 1,
  });
}
