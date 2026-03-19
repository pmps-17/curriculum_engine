import { NextRequest, NextResponse } from "next/server";
import { endpoints } from "@/lib/config";
import { getSessionEmail, getBackendAuthHeaders } from "@/lib/auth";

/**
 * GET /api/documents?organization_id=...&limit=...&offset=...
 *
 * Proxies to GET /api/v1/documents on the backend.
 */
export async function GET(req: NextRequest): Promise<NextResponse> {
  const email = await getSessionEmail();
  if (!email) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  // Forward query string as-is
  const qs = req.nextUrl.searchParams.toString();
  const backendUrl = `${endpoints.documents()}${qs ? `?${qs}` : ""}`;
  const authHeaders = await getBackendAuthHeaders();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, {
      method: "GET",
      headers: { Accept: "application/json", ...authHeaders },
      signal: AbortSignal.timeout(10_000),
    });
  } catch (err) {
    console.error("[documents] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}
