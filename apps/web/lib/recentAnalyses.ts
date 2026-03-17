/**
 * Lightweight localStorage helper for recent analysis runs.
 *
 * Stores a capped list of completed analysis metadata so the Compare
 * page can show a selection UI without a backend "list runs" endpoint.
 *
 * ─── Future migration ───────────────────────────────────────────────
 * When a backend endpoint like
 *   GET /api/v1/analysis-runs?organization_id=...
 * is available, replace `getRecentAnalyses()` with a fetch call.
 * The shape of `RecentAnalysis` stays the same, so the Compare page
 * and CompareSelector component need zero changes.
 */

const STORAGE_KEY = "recent_analyses";
const MAX_ITEMS = 50;

export interface RecentAnalysis {
  analysis_run_id: string;
  title: string;
  subject: string;
  grade_band: string;
  created_at: string; // ISO string
  organization_id?: string;
}

/** Read all recent analyses from localStorage. */
export function getRecentAnalyses(): RecentAnalysis[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as RecentAnalysis[];
  } catch {
    return [];
  }
}

/** Get analyses filtered to a specific organization. */
export function getRecentForOrganization(organizationId: string): RecentAnalysis[] {
  return getRecentAnalyses().filter(
    (a) => a.organization_id === organizationId,
  );
}

/** Prepend a new analysis (deduplicates by run ID, caps at MAX_ITEMS). */
export function saveRecentAnalysis(item: RecentAnalysis): void {
  if (typeof window === "undefined") return;
  const existing = getRecentAnalyses().filter(
    (a) => a.analysis_run_id !== item.analysis_run_id,
  );
  const updated = [item, ...existing].slice(0, MAX_ITEMS);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
}
