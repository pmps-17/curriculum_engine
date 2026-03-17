"use client";

interface OrganizationCardProps {
  name: string;
  organizationId: string;
  inviteCode?: string | null;
  createdAt?: string | null;
  isActive: boolean;
  onOpen: () => void;
}

export default function OrganizationCard({
  name,
  inviteCode,
  createdAt,
  isActive,
  onOpen,
}: OrganizationCardProps) {
  return (
    <div
      className={`group relative flex flex-col justify-between rounded-xl border bg-white p-5 shadow-sm transition hover:shadow-md ${
        isActive
          ? "border-[#4F46E5]/40 ring-2 ring-[#4F46E5]/10"
          : "border-gray-200"
      }`}
    >
      {/* Active badge */}
      {isActive && (
        <span className="absolute right-3 top-3 inline-flex items-center gap-1 rounded-full bg-[#10B981]/10 px-2 py-0.5 text-[10px] font-semibold text-[#10B981]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#10B981]" />
          Active
        </span>
      )}

      {/* Org info */}
      <div>
        <h3 className="text-[15px] font-semibold text-gray-900 pr-16 truncate">
          {name}
        </h3>

        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
          {inviteCode && (
            <span className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 font-mono text-[11px] text-gray-500">
              <svg className="h-3 w-3 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
              </svg>
              {inviteCode}
            </span>
          )}
          {createdAt && (
            <span className="text-[11px] text-gray-400">
              Created {new Date(createdAt).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>

      {/* Open button */}
      <button
        type="button"
        onClick={onOpen}
        className={`mt-4 flex h-9 w-full items-center justify-center rounded-lg text-sm font-semibold transition ${
          isActive
            ? "bg-[#4F46E5] text-white hover:bg-[#4338CA]"
            : "border border-gray-200 bg-gray-50 text-gray-700 hover:border-[#4F46E5] hover:bg-[#4F46E5]/5 hover:text-[#4F46E5]"
        }`}
      >
        {isActive ? "Continue" : "Open"}
      </button>
    </div>
  );
}
