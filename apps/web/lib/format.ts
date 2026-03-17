/**
 * Shared formatting helpers for scores and percentages.
 *
 * Used by PillarCards, SkillList, and anywhere else scores are displayed.
 */

/** Format a 0–1 score as a percentage string, or "—" if missing. */
export function pct(v?: number | null): string {
  return v != null ? `${Math.round(v * 100)}%` : "—";
}

/** Tailwind colour class based on score threshold. */
export function scoreColor(score?: number | null): string {
  if (score == null) return "text-gray-400";
  if (score >= 0.7) return "text-[#10B981]";
  if (score >= 0.4) return "text-amber-500";
  return "text-red-500";
}
