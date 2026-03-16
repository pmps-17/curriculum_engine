import AnalyzeForm from "@/components/AnalyzeForm";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-3xl flex-col gap-1 px-6 py-8">
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            Curriculum <span className="text-[#4F46E5]">Engine</span>
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
