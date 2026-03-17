"use client";

import { useState, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Props                                                             */
/* ------------------------------------------------------------------ */

interface Props {
  open: boolean;
  initial: { title: string; subject: string; grade_band: string };
  onSave: (updated: { title: string; subject: string; grade_band: string }) => void;
  onClose: () => void;
}

/* ------------------------------------------------------------------ */
/*  Shared styles                                                     */
/* ------------------------------------------------------------------ */

const INPUT =
  "h-10 w-full rounded-lg border border-gray-200 bg-white px-3.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20";

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function EditDetailsModal({ open, initial, onSave, onClose }: Props) {
  const [title, setTitle] = useState(initial.title);
  const [subject, setSubject] = useState(initial.subject);
  const [gradeBand, setGradeBand] = useState(initial.grade_band);

  // Sync when modal opens with new data
  useEffect(() => {
    if (open) {
      setTitle(initial.title);
      setSubject(initial.subject);
      setGradeBand(initial.grade_band);
    }
  }, [open, initial]);

  if (!open) return null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSave({ title: title.trim(), subject: subject.trim(), grade_band: gradeBand.trim() });
  }

  function handleBackdrop(e: React.MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
      onClick={handleBackdrop}
    >
      <div className="w-full max-w-md rounded-2xl border border-gray-200/80 bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-bold text-gray-900">Edit Details</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          {/* Note about backend */}
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-700">
            Changes are saved locally. A backend PATCH endpoint is needed
            to persist edits across sessions.
          </p>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">Title</label>
            <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} className={INPUT} />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">Subject</label>
            <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)} className={INPUT} />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">Grade Band</label>
            <input type="text" value={gradeBand} onChange={(e) => setGradeBand(e.target.value)} className={INPUT} />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="h-9 rounded-lg px-4 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="h-9 rounded-lg bg-[#4F46E5] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA]"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
