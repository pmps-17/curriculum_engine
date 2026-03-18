"use client";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

export interface CurriculumSetData {
  id: string;
  organization_id: string;
  title: string;
  subject: string | null;
  grade_band: string | null;
  description: string | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

interface CurriculumSetCardProps {
  set: CurriculumSetData;
  onClick: (set: CurriculumSetData) => void;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function timeAgo(iso: string): string {
  const d = new Date(iso);
  const now = Date.now();
  const diff = now - d.getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function CurriculumSetCard({ set, onClick }: CurriculumSetCardProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onClick(set)}
      onKeyDown={(e) => { if (e.key === "Enter") onClick(set); }}
      className="group flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition cursor-pointer hover:shadow-md hover:border-[#4F46E5]/30"
    >
      {/* Title */}
      <h3 className="truncate text-[15px] font-semibold text-gray-900 group-hover:text-[#4F46E5] transition">
        {set.title}
      </h3>

      {/* Description */}
      {set.description && (
        <p className="mt-1 line-clamp-2 text-xs text-gray-500">
          {set.description}
        </p>
      )}

      {/* Meta chips */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {set.subject && (
          <span className="inline-flex items-center gap-1 rounded-full bg-[#4F46E5]/5 px-2.5 py-0.5 text-[11px] font-medium text-[#4F46E5]">
            <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
            </svg>
            {set.subject}
          </span>
        )}
        {set.grade_band && (
          <span className="inline-flex items-center gap-1 rounded-full bg-[#10B981]/5 px-2.5 py-0.5 text-[11px] font-medium text-[#10B981]">
            <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.636 50.636 0 00-2.658-.813A59.906 59.906 0 0112 3.493a59.903 59.903 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0112 13.489a50.702 50.702 0 017.74-3.342" />
            </svg>
            Grades {set.grade_band}
          </span>
        )}
      </div>

      {/* Footer */}
      <div className="mt-auto pt-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-gray-400">
            Created {timeAgo(set.created_at)}
          </span>
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[#4F46E5] opacity-0 transition group-hover:opacity-100">
            Open
            <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
          </span>
        </div>
      </div>
    </div>
  );
}
