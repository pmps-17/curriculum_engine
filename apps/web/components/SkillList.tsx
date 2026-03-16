import type { SkillScore } from "@/features/results/hooks";
import { pct, scoreColor } from "@/lib/format";

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

interface Props {
  skills: SkillScore[];
}

export default function SkillList({ skills }: Props) {
  if (skills.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">No skill scores available.</p>
    );
  }

  return (
    <ul className="divide-y divide-gray-100">
      {skills.map((s, i) => (
        <li
          key={s.skill_code ?? s.skill_id ?? i}
          className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3 first:pt-0 last:pb-0"
        >
          {/* Name + code */}
          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <span className="truncate text-sm font-medium text-gray-800">
              {s.skill_name ?? s.skill_code ?? "Unnamed Skill"}
            </span>
            {s.skill_code && s.skill_name && (
              <span className="text-xs text-gray-400">{s.skill_code}</span>
            )}
          </div>

          {/* Taught / Assessed badges */}
          <div className="flex gap-1.5">
            {s.taught_flag && (
              <span className="rounded-full bg-[#4F46E5]/10 px-2.5 py-0.5 text-[11px] font-semibold text-[#4F46E5]">
                Taught
              </span>
            )}
            {s.assessed_flag && (
              <span className="rounded-full bg-[#10B981]/10 px-2.5 py-0.5 text-[11px] font-semibold text-[#10B981]">
                Assessed
              </span>
            )}
          </div>

          {/* Score + confidence */}
          <div className="flex items-center gap-3 text-right">
            <span className={`text-sm font-bold tabular-nums ${scoreColor(s.score)}`}>
              {pct(s.score)}
            </span>
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-500">
              conf {pct(s.confidence)}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}
