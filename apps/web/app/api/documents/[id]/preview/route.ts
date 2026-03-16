import { NextRequest, NextResponse } from "next/server";
import { endpoints } from "@/lib/config";
import { getBackendAuthHeaders } from "@/lib/auth";

/**
 * GET /api/documents/:id/preview
 *
 * Proxies to GET /api/v1/documents/:id/preview on the backend.
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const authHeaders = await getBackendAuthHeaders();

  if (!Object.keys(authHeaders).length) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(endpoints.documentPreview(id), {
      method: "GET",
      headers: { Accept: "application/json", ...authHeaders },
      signal: AbortSignal.timeout(15_000),
    });
  } catch (err) {
    console.error("[documents/preview] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}
