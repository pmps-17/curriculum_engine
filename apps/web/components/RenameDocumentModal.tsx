"use client";

import { useState, useEffect, useRef } from "react";
import type { DocumentFields } from "@/lib/documents";

export type { DocumentFields };

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

interface Props {
  open: boolean;
  initial: DocumentFields;
  error?: string;
  onClose: () => void;
  onSave: (fields: DocumentFields) => Promise<void> | void;
}

/* ------------------------------------------------------------------ */
/*  Shared styles                                                     */
/* ------------------------------------------------------------------ */

const INPUT =
  "w-full rounded-lg border border-gray-200 px-3.5 py-2.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/30";

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function RenameDocumentModal({
  open,
  initial,
  error,
  onClose,
  onSave,
}: Props) {
  const [form, setForm] = useState<DocumentFields>(initial);
  const [saving, setSaving] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);

  /* Reset form when modal opens with new data */
  useEffect(() => {
    if (open) {
      setForm(initial);
      setTimeout(() => titleRef.current?.select(), 50);
    }
  }, [open, initial]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(form);
      onClose();
    } catch {
      /* parent handles toast */
    } finally {
      setSaving(false);
    }
  }

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      {/* Panel */}
      <div
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-gray-900">Edit Document</h2>
        <p className="mt-1 text-sm text-gray-500">
          Update the display title, subject, or grade band.
        </p>

        {error && (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-600">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {/* Title */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="rename-title" className="text-sm font-medium text-gray-700">
              Title
            </label>
            <input
              ref={titleRef}
              id="rename-title"
              type="text"
              maxLength={500}
              value={form.title ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              className={INPUT}
              placeholder="Document title"
            />
          </div>

          {/* Subject */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="rename-subject" className="text-sm font-medium text-gray-700">
              Subject
            </label>
            <input
              id="rename-subject"
              type="text"
              maxLength={255}
              value={form.subject ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
              className={INPUT}
              placeholder="e.g. Science"
            />
          </div>

          {/* Grade Band */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="rename-grade" className="text-sm font-medium text-gray-700">
              Grade Band
            </label>
            <input
              id="rename-grade"
              type="text"
              maxLength={100}
              value={form.grade_band ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, grade_band: e.target.value }))}
              className={INPUT}
              placeholder="e.g. 3-5"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-[#4F46E5] px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-[#4338CA] disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
