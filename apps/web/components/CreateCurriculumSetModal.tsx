"use client";

import { useState } from "react";
import { proxyPaths } from "@/lib/config";

/* ------------------------------------------------------------------ */
/*  Props                                                             */
/* ------------------------------------------------------------------ */

interface CreateCurriculumSetModalProps {
  open: boolean;
  organizationId: string;
  onClose: () => void;
  onCreated: () => void;
}

/* ------------------------------------------------------------------ */
/*  Shared styles                                                     */
/* ------------------------------------------------------------------ */

const INPUT =
  "h-10 w-full rounded-lg border border-gray-200 bg-white px-3.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20";

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function CreateCurriculumSetModal({
  open,
  organizationId,
  onClose,
  onCreated,
}: CreateCurriculumSetModalProps) {
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [gradeBand, setGradeBand] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  function handleClose() {
    setTitle("");
    setSubject("");
    setGradeBand("");
    setDescription("");
    setError("");
    setLoading(false);
    onClose();
  }

  function handleBackdrop(e: React.MouseEvent) {
    if (e.target === e.currentTarget) handleClose();
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setError("Title is required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch(proxyPaths.curriculumSets, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          organization_id: organizationId,
          title: title.trim(),
          subject: subject.trim() || null,
          grade_band: gradeBand.trim() || null,
          description: description.trim() || null,
        }),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => null);
        throw new Error(b?.detail ?? b?.error ?? `Error ${res.status}`);
      }
      handleClose();
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create set.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 backdrop-blur-sm px-4 py-10"
      onClick={handleBackdrop}
    >
      <div className="w-full max-w-md rounded-2xl border border-gray-200/80 bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <div>
            <h2 className="text-base font-bold text-gray-900">New Curriculum Set</h2>
            <p className="mt-0.5 text-xs text-gray-500">
              Create a set to organize curriculum documents.
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-lg p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          {/* Title (required) */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">
              Title <span className="text-[#4F46E5]">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => { setTitle(e.target.value); setError(""); }}
              placeholder="e.g. Grade 5 Science Unit"
              className={INPUT}
              autoFocus
            />
          </div>

          {/* Subject + Grade Band */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">Subject</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. Science"
                className={INPUT}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">Grade Band</label>
              <input
                type="text"
                value={gradeBand}
                onChange={(e) => setGradeBand(e.target.value)}
                placeholder="e.g. 3-5"
                className={INPUT}
              />
            </div>
          </div>

          {/* Description */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">
              Description <span className="text-gray-400">(optional)</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Short description of this curriculum set…"
              className="w-full rounded-lg border border-gray-200 bg-white px-3.5 py-2.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20 resize-none"
            />
          </div>

          {/* Error */}
          {error && <p className="text-xs text-red-500">{error}</p>}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              className="h-9 rounded-lg px-4 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !title.trim()}
              className="flex h-9 items-center gap-2 rounded-lg bg-[#4F46E5] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading && (
                <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              )}
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
