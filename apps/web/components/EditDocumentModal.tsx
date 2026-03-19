"use client";

import { useState, useEffect, useRef } from "react";
import type {
  DocumentFields,
  DocumentLibraryItem,
  DocumentDetail,
} from "@/lib/documents";
import {
  getDocumentDetail,
  updateDocumentMetadata,
  updateDocumentContent,
} from "@/lib/documents";

/* ------------------------------------------------------------------ */
/*  Props                                                             */
/* ------------------------------------------------------------------ */

interface Props {
  open: boolean;
  item: DocumentLibraryItem | null;
  onClose: () => void;
  /** Called after a successful save so the parent can refresh. */
  onSaved: () => void;
}

/* ------------------------------------------------------------------ */
/*  Shared styles                                                     */
/* ------------------------------------------------------------------ */

const INPUT =
  "w-full rounded-lg border border-gray-200 px-3.5 py-2.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/30";

const TAB_ACTIVE =
  "rounded-md bg-white px-3 py-1.5 text-xs font-medium text-[#4F46E5] shadow-sm";
const TAB_INACTIVE =
  "rounded-md px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-700";

type ContentMode = "text" | "file";

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function EditDocumentModal({
  open,
  item,
  onClose,
  onSaved,
}: Props) {
  /* ── Metadata form state ──────────────────────────────────────── */
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [gradeBand, setGradeBand] = useState("");
  const [description, setDescription] = useState(""); // UI-only (no backend column)

  /* ── Detail fetch state ───────────────────────────────────────── */
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  /* ── Content editing state ────────────────────────────────────── */
  const [contentMode, setContentMode] = useState<ContentMode>("text");
  const [editedText, setEditedText] = useState("");
  const [replaceFile, setReplaceFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /* ── Save state ───────────────────────────────────────────────── */
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const titleRef = useRef<HTMLInputElement>(null);

  /* ── Initialise form when modal opens ─────────────────────────── */
  useEffect(() => {
    if (!open || !item) return;

    setTitle(item.title || item.filename || "");
    setSubject(item.subject || "");
    setGradeBand(item.grade_band || "");
    setDescription("");
    setDetail(null);
    setEditedText("");
    setReplaceFile(null);
    setContentMode("text");
    setError("");
    setTimeout(() => titleRef.current?.select(), 50);

    // Fetch full detail (including extracted_text)
    setDetailLoading(true);
    getDocumentDetail(item.document_id)
      .then((d) => {
        setDetail(d);
        setEditedText(d.extracted_text ?? "");
        if (d.title) setTitle(d.title);
        if (d.subject) setSubject(d.subject);
        if (d.grade_band) setGradeBand(d.grade_band);
      })
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false));
  }, [open, item]);

  if (!open || !item) return null;

  /* ── Dirty detection ──────────────────────────────────────────── */
  const metadataDirty =
    (title.trim() || undefined) !== (detail?.title ?? item.title ?? item.filename ?? undefined) ||
    (subject.trim() || undefined) !== (detail?.subject ?? item.subject ?? undefined) ||
    (gradeBand.trim() || undefined) !== (detail?.grade_band ?? item.grade_band ?? undefined);

  const contentDirty =
    contentMode === "file"
      ? replaceFile !== null
      : editedText !== (detail?.extracted_text ?? "");

  /* ── Save ─────────────────────────────────────────────────────── */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");

    try {
      // 1. Metadata changes
      if (metadataDirty) {
        const fields: DocumentFields = {
          title: title.trim() || undefined,
          subject: subject.trim() || undefined,
          grade_band: gradeBand.trim() || undefined,
        };
        await updateDocumentMetadata(item!.document_id, fields);
      }

      // 2. Content changes
      if (contentDirty) {
        if (contentMode === "file" && replaceFile) {
          await updateDocumentContent(item!.document_id, {
            file: replaceFile,
          });
        } else if (contentMode === "text") {
          await updateDocumentContent(item!.document_id, {
            curriculum_text: editedText,
          });
        }
      }

      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save changes.");
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
      {/* Panel — wider to accommodate content area */}
      <div
        className="flex w-full max-w-2xl max-h-[90vh] flex-col rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-0">
          <h2 className="text-lg font-semibold text-gray-900">Edit Document</h2>
          <p className="mt-1 text-sm text-gray-500">
            Update metadata and content for{" "}
            <span className="font-medium text-gray-700">{item.filename}</span>.
          </p>
        </div>

        {error && (
          <div className="mx-6 mt-3 rounded-lg border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-600">
            {error}
          </div>
        )}

        {/* Scrollable body */}
        <form onSubmit={handleSubmit} className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
            {/* ── Metadata section ──────────────────────────────── */}
            <fieldset className="space-y-4">
              <legend className="text-sm font-semibold text-gray-800">Metadata</legend>

              {/* Title */}
              <div className="flex flex-col gap-1.5">
                <label htmlFor="edit-title" className="text-sm font-medium text-gray-700">
                  Title
                </label>
                <input
                  ref={titleRef}
                  id="edit-title"
                  type="text"
                  maxLength={500}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className={INPUT}
                  placeholder="Document title"
                />
              </div>

              {/* Subject */}
              <div className="flex flex-col gap-1.5">
                <label htmlFor="edit-subject" className="text-sm font-medium text-gray-700">
                  Subject
                </label>
                <input
                  id="edit-subject"
                  type="text"
                  maxLength={255}
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className={INPUT}
                  placeholder="e.g. Science"
                />
              </div>

              {/* Grade Band */}
              <div className="flex flex-col gap-1.5">
                <label htmlFor="edit-grade" className="text-sm font-medium text-gray-700">
                  Grade Band
                </label>
                <input
                  id="edit-grade"
                  type="text"
                  maxLength={100}
                  value={gradeBand}
                  onChange={(e) => setGradeBand(e.target.value)}
                  className={INPUT}
                  placeholder="e.g. 3-5"
                />
              </div>

              {/* Description (optional, UI-only) */}
              <div className="flex flex-col gap-1.5">
                <label htmlFor="edit-description" className="text-sm font-medium text-gray-700">
                  Description{" "}
                  <span className="text-xs font-normal text-gray-400">(optional)</span>
                </label>
                <textarea
                  id="edit-description"
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className={`resize-y ${INPUT}`}
                  placeholder="Brief description…"
                />
              </div>
            </fieldset>

            {/* ── Curriculum Content section ─────────────────────── */}
            <fieldset className="space-y-3">
              <legend className="text-sm font-semibold text-gray-800">
                Curriculum Content
              </legend>

              {detailLoading ? (
                <div className="flex items-center gap-2 text-sm text-gray-400 py-4">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Loading content…
                </div>
              ) : (
                <>
                  {/* Mode tabs */}
                  <div className="inline-flex rounded-lg bg-gray-100 p-0.5">
                    <button
                      type="button"
                      onClick={() => setContentMode("text")}
                      className={contentMode === "text" ? TAB_ACTIVE : TAB_INACTIVE}
                    >
                      Preview / Edit Text
                    </button>
                    <button
                      type="button"
                      onClick={() => setContentMode("file")}
                      className={contentMode === "file" ? TAB_ACTIVE : TAB_INACTIVE}
                    >
                      Replace File
                    </button>
                  </div>

                  {contentMode === "text" && (
                    <div className="flex flex-col gap-1.5">
                      <textarea
                        id="edit-content-text"
                        rows={8}
                        value={editedText}
                        onChange={(e) => setEditedText(e.target.value)}
                        className={`resize-y font-mono text-xs ${INPUT}`}
                        placeholder={
                          detail?.extraction_status === "EXTRACTED"
                            ? "Edit extracted text…"
                            : "Paste curriculum text…"
                        }
                      />
                      {editedText && (
                        <span className="text-xs text-gray-400">
                          {editedText.length.toLocaleString()} characters
                        </span>
                      )}
                    </div>
                  )}

                  {contentMode === "file" && (
                    <div className="flex flex-col gap-2">
                      <p className="text-xs text-gray-500">
                        Upload a new PDF, DOCX, or TXT file to replace the current content.
                        Text will be re-extracted automatically.
                      </p>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf,.docx,.doc,.txt,.md,.html"
                        onChange={(e) => setReplaceFile(e.target.files?.[0] ?? null)}
                        className="block w-full text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-[#4F46E5]/5 file:px-3 file:py-2 file:text-xs file:font-medium file:text-[#4F46E5] hover:file:bg-[#4F46E5]/10"
                      />
                      {replaceFile && (
                        <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm">
                          <span className="truncate text-gray-700">{replaceFile.name}</span>
                          <button
                            type="button"
                            onClick={() => {
                              setReplaceFile(null);
                              if (fileInputRef.current) fileInputRef.current.value = "";
                            }}
                            className="ml-2 shrink-0 text-xs text-red-500 hover:text-red-700"
                          >
                            Remove
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </fieldset>
          </div>

          {/* Actions — pinned to bottom */}
          <div className="flex items-center justify-end gap-3 border-t border-gray-100 px-6 py-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || detailLoading}
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
