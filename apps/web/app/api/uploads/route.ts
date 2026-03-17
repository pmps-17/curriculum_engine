import { NextRequest, NextResponse } from "next/server";
import { endpoints } from "@/lib/config";
import { getSessionEmail, getBackendAuthHeaders } from "@/lib/auth";

const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB

/**
 * POST /api/uploads
 *
 * Proxies file uploads to the backend API with production-quality error handling.
 *
 * Request:
 * - multipart/form-data with fields:
 *   - file (required, binary)
 *   - title (optional, string)
 *   - subject (optional, string)
 *   - grade_band (optional, string)
 *   - school_id (optional, UUID)
 *
 * Response (success 200):
 * {
 *   "document_id": "uuid",
 *   "filename": "...",
 *   "content_type": "...",
 *   "size_bytes": 123,
 *   "extraction_status": "EXTRACTED" | "STORED_ONLY" | "REJECTED",
 *   "extracted_text": "..." (optional, only when extracted),
 *   "warnings": ["..."] (optional)
 * }
 *
 * Errors:
 * - 400: missing file or invalid input
 * - 413: file too large (> 25MB)
 * - 502: backend unreachable
 * - 5xx: backend error (proxied)
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    // 0. Authenticate via session
    const email = await getSessionEmail();
    if (!email) {
      return NextResponse.json({ error: "Not authenticated." }, { status: 401 });
    }

    // 1. Parse multipart/form-data from browser
    let formData: FormData;
    try {
      formData = await request.formData();
    } catch (err) {
      return NextResponse.json({ error: "Invalid multipart/form-data" }, { status: 400 });
    }

    // 2. Validate file exists and is not empty
    const file = formData.get("file") as File | null;
    if (!file || file.size === 0) {
      return NextResponse.json(
        { error: "File is required and must not be empty" },
        { status: 400 }
      );
    }

    // 3. Guard: reject files > 25MB
    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        {
          error: `File exceeds 25MB limit (got ${(file.size / 1024 / 1024).toFixed(2)}MB)`,
        },
        { status: 413 }
      );
    }

    // 4. Build new FormData for backend
    // (Re-create to ensure clean multipart encoding)
    const backendFormData = new FormData();
    backendFormData.append("file", file);

    // Add optional metadata fields if present
    const title = formData.get("title");
    if (title && typeof title === "string" && title.trim()) {
      backendFormData.append("title", title);
    }

    const subject = formData.get("subject");
    if (subject && typeof subject === "string" && subject.trim()) {
      backendFormData.append("subject", subject);
    }

    const grade_band = formData.get("grade_band");
    if (grade_band && typeof grade_band === "string" && grade_band.trim()) {
      backendFormData.append("grade_band", grade_band);
    }

    const school_id = formData.get("school_id");
    if (school_id && typeof school_id === "string" && school_id.trim()) {
      backendFormData.append("school_id", school_id);
    }

    const organization_id = formData.get("organization_id");
    if (organization_id && typeof organization_id === "string" && organization_id.trim()) {
      backendFormData.append("organization_id", organization_id);
    }

    // 5. Forward to backend
    const backendUrl = endpoints.uploads();

    // Build auth headers (id_token + X-User-Email for dual-mode compat)
    const backendHeaders = await getBackendAuthHeaders();

    let backendResponse: Response;
    try {
      backendResponse = await fetch(backendUrl, {
        method: "POST",
        // Do NOT set Content-Type; fetch will add the correct multipart boundary
        headers: backendHeaders,
        body: backendFormData,
      });
    } catch (err) {
      // Network error: backend unreachable
      console.error("[uploads] Backend fetch failed:", err);
      return NextResponse.json(
        {
          error: "Backend service unavailable",
        },
        { status: 502 }
      );
    }

    // 6. Parse and return backend response
    // Note: Do not log file content or extracted_text for privacy
    const backendBody = await backendResponse.json().catch(() => null);

    // Preserve backend status code
    return NextResponse.json(backendBody, { status: backendResponse.status });
  } catch (err) {
    // Unexpected error
    console.error("[uploads] Unexpected error:", err);
    return NextResponse.json(
      {
        error: "Internal server error",
      },
      { status: 500 }
    );
  }
}
