"use client";

import AnalyzeForm from "@/components/AnalyzeForm";

export default function HomePage() {
  // AppShell handles the org-guard redirect — this page only renders
  // when an organization is already selected.
  return (
    <main className="min-h-[calc(100vh-49px)] bg-gray-50">
      {/* Page header */}
      <header className="border-b border-gray-200/60 bg-white">
        <div className="mx-auto flex max-w-3xl flex-col gap-1 px-6 py-8">
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            Analyze <span className="text-[#4F46E5]">Curriculum</span>
          </h1>
          <p className="text-sm text-gray-500">
            Submit curriculum content for automated compliance analysis.
          </p>
        </div>
      </header>

      {/* Form card */}
      <div className="mx-auto max-w-3xl px-6 py-10">
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
          <AnalyzeForm />
        </div>
      </div>
    </main>
  );
}
