import type { PillarScore } from "@/features/results/hooks";
import { pct, scoreColor } from "@/lib/format";

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

interface Props {
  pillars: PillarScore[];
}

export default function PillarCards({ pillars }: Props) {
  if (pillars.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">No pillar scores available.</p>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {pillars.map((p, i) => (
        <div
          key={p.pillar_code ?? i}
          className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
        >
          {/* Code badge */}
          {p.pillar_code && (
            <span className="w-fit rounded-md bg-[#4F46E5]/10 px-2 py-0.5 text-xs font-semibold text-[#4F46E5]">
              {p.pillar_code}
            </span>
          )}

          {/* Name */}
          <h3 className="text-sm font-medium text-gray-800 leading-snug">
            {p.pillar_name ?? "Unnamed Pillar"}
          </h3>

          {/* Score + confidence */}
          <div className="mt-auto flex items-end justify-between">
            <span className={`text-2xl font-bold tabular-nums ${scoreColor(p.score)}`}>
              {pct(p.score)}
            </span>
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-500">
              conf {pct(p.confidence)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
