import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL } from "@/lib/config";
import { getSessionEmail, getBackendAuthHeaders } from "@/lib/auth";

/**
 * GET /api/analysis-runs?organization_id=...&limit=...&offset=...
 *
 * Proxies to the FastAPI backend at
 * GET /api/v1/analysis-runs?organization_id=...&limit=...&offset=...
 *
 * Reads auth credentials from the NextAuth session (server-side).
 */
export async function GET(req: NextRequest) {
  const email = await getSessionEmail();
  if (!email) {
    return NextResponse.json(
      { error: "Not authenticated." },
      { status: 401 },
    );
  }

  // Forward query params as-is
  const { searchParams } = req.nextUrl;
  const qs = searchParams.toString();
  const backendUrl = `${API_BASE_URL}/api/v1/analysis-runs${qs ? `?${qs}` : ""}`;
  const authHeaders = await getBackendAuthHeaders();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...authHeaders,
      },
      signal: AbortSignal.timeout(15_000),
    });
  } catch (err) {
    console.error("[analysis-runs] Backend unreachable:", err);
    return NextResponse.json(
      {
        error: "BACKEND_UNREACHABLE",
        detail:
          err instanceof Error ? err.message : "Could not connect to backend.",
      },
      { status: 502 },
    );
  }

  const contentType = upstream.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  }

  const text = await upstream.text();
  return new NextResponse(text, { status: upstream.status });
}
