/**
 * Document types and API helpers.
 *
 * Single source of truth for editable document metadata and all
 * document-related client-side API calls.  Every component that
 * reads or mutates documents should import from here.
 */

import { z } from "zod";
import { apiFetch, ApiError } from "@/lib/api";
import { proxyPaths } from "@/lib/config";

/* ------------------------------------------------------------------ */
/*  Editable-fields schema (shared by Upload page + Edit modal)       */
/* ------------------------------------------------------------------ */

export const DocumentFieldsSchema = z.object({
  title: z.string().max(500).optional(),
  subject: z.string().max(255).optional(),
  grade_band: z.string().max(100).optional(),
});

export type DocumentFields = z.infer<typeof DocumentFieldsSchema>;

/* ------------------------------------------------------------------ */
/*  Response types                                                    */
/* ------------------------------------------------------------------ */

/** Shape returned by GET /api/documents?organization_id=… */
export interface DocumentLibraryItem {
  document_id: string;
  title: string | null;
  filename: string;
  content_type: string | null;
  size_bytes: number | null;
  extraction_status: string;
  subject: string | null;
  grade_band: string | null;
  curriculum_set_id: string | null;
  created_at: string;
  latest_analysis_run_id: string | null;
  latest_analysis_status: string | null;
}

/** Shape returned by POST /api/uploads */
export interface UploadResponse {
  document_id: string;
  filename: string;
  content_type?: string;
  size_bytes?: number;
  extraction_status: "EXTRACTED" | "STORED_ONLY" | "REJECTED";
  warnings?: string[];
  preview_text?: string | null;
  preview_truncated?: boolean | null;
}

/** Full detail returned by GET /api/documents/:id */
export interface DocumentDetail {
  document_id: string;
  filename: string;
  content_type: string | null;
  size_bytes: number | null;
  document_type: string;
  extraction_status: string;
  warnings: string | null;
  organization_id: string | null;
  created_at: string;
  title: string | null;
  subject: string | null;
  grade_band: string | null;
  extracted_text: string | null;
}

/** Response from PATCH /api/documents/:id/content */
export interface DocumentContentResponse {
  document_id: string;
  extraction_status: string;
  char_count: number | null;
}

/* ------------------------------------------------------------------ */
/*  API helpers                                                       */
/* ------------------------------------------------------------------ */

/**
 * Upload a file and create a document record.
 *
 * Uses multipart/form-data — caller builds a FormData with at least
 * a `file` entry.  `organizationId` and optional metadata fields are
 * appended automatically.
 */
export async function uploadDocument(
  organizationId: string,
  file: File,
  fields?: DocumentFields,
): Promise<UploadResponse> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("organization_id", organizationId);
  if (fields?.title) fd.append("title", fields.title);
  if (fields?.subject) fd.append("subject", fields.subject);
  if (fields?.grade_band) fd.append("grade_band", fields.grade_band);

  const res = await fetch(proxyPaths.uploads, {
    method: "POST",
    body: fd,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body);
  }

  return res.json() as Promise<UploadResponse>;
}

/**
 * List documents for an organization (library grid).
 */
export async function listDocuments(
  organizationId: string,
  opts: { limit?: number; offset?: number } = {},
): Promise<DocumentLibraryItem[]> {
  const limit = opts.limit ?? 200;
  const offset = opts.offset ?? 0;
  const res = await fetch(
    `${proxyPaths.documents}?organization_id=${organizationId}&limit=${limit}&offset=${offset}`,
  );
  if (!res.ok) throw new Error(`Error ${res.status}`);
  return res.json() as Promise<DocumentLibraryItem[]>;
}

/**
 * Patch user-facing metadata (title, subject, grade_band).
 *
 * Sends only the provided fields.  Pass `null` for a field value
 * to clear it on the backend.
 */
export function updateDocumentMetadata(
  documentId: string,
  fields: Partial<DocumentFields>,
): Promise<DocumentLibraryItem> {
  return apiFetch<DocumentLibraryItem>(proxyPaths.documentPatch(documentId), {
    method: "PATCH",
    body: {
      title: fields.title ?? null,
      subject: fields.subject ?? null,
      grade_band: fields.grade_band ?? null,
    },
  });
}

/**
 * Soft-delete a document.
 */
export async function deleteDocument(documentId: string): Promise<void> {
  const res = await fetch(proxyPaths.documentPatch(documentId), {
    method: "DELETE",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(
      (body as { detail?: string } | null)?.detail ??
        `Delete failed (${res.status})`,
    );
  }
}

/* ------------------------------------------------------------------ */
/*  Preview                                                           */
/* ------------------------------------------------------------------ */

export interface DocumentPreview {
  document_id: string;
  preview_text: string;
  preview_truncated: boolean;
  char_count: number;
}

/**
 * Fetch a truncated text preview for a document.
 *
 * Returns `null` when text has not been extracted (409 from backend).
 */
export async function getDocumentPreview(
  documentId: string,
): Promise<DocumentPreview | null> {
  const res = await fetch(proxyPaths.documentPreview(documentId));
  if (res.status === 409) return null; // not extracted
  if (!res.ok) throw new Error(`Preview failed (${res.status})`);
  return res.json() as Promise<DocumentPreview>;
}

/* ------------------------------------------------------------------ */
/*  Document detail (full text)                                       */
/* ------------------------------------------------------------------ */

/**
 * Fetch full document detail including extracted text.
 */
export async function getDocumentDetail(
  documentId: string,
): Promise<DocumentDetail> {
  const res = await fetch(proxyPaths.documentPatch(documentId));
  if (!res.ok) throw new Error(`Detail failed (${res.status})`);
  return res.json() as Promise<DocumentDetail>;
}

/* ------------------------------------------------------------------ */
/*  Content replacement                                               */
/* ------------------------------------------------------------------ */

/**
 * Replace document content — either pasted text or a new file.
 *
 * Sends multipart/form-data with either `curriculum_text` or `file`.
 */
export async function updateDocumentContent(
  documentId: string,
  payload: { curriculum_text: string } | { file: File },
): Promise<DocumentContentResponse> {
  const fd = new FormData();
  if ("curriculum_text" in payload) {
    fd.append("curriculum_text", payload.curriculum_text);
  } else {
    fd.append("file", payload.file);
  }

  const res = await fetch(proxyPaths.documentContent(documentId), {
    method: "PATCH",
    body: fd,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(
      (body as { detail?: string } | null)?.detail ??
        `Content update failed (${res.status})`,
    );
  }

  return res.json() as Promise<DocumentContentResponse>;
}
