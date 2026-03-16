import { NextRequest, NextResponse } from "next/server";
import { endpoints } from "@/lib/config";
import { getBackendAuthHeaders } from "@/lib/auth";

/**
 * GET /api/results/:analysisRunId
 *
 * Proxies result fetches to the FastAPI backend at
 * GET /api/v1/results/{analysisRunId}.
 *
 * - Reads auth credentials from the NextAuth session (server-side).
 * - Backend 4xx/5xx responses are returned as-is (status + JSON body).
 * - Network errors return 502 with { error: "BACKEND_UNREACHABLE" }.
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ analysisRunId: string }> },
) {
  const { analysisRunId } = await params;
  const backendUrl = endpoints.results(analysisRunId);

  const authHeaders = await getBackendAuthHeaders();

  let upstream: Response;
  try {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...authHeaders,
    };

    upstream = await fetch(backendUrl, {
      method: "GET",
      headers,
      signal: AbortSignal.timeout(30_000),
    });
  } catch (err) {
    console.error("[results] Backend unreachable:", err);
    return NextResponse.json(
      {
        error: "BACKEND_UNREACHABLE",
        detail:
          err instanceof Error ? err.message : "Could not connect to backend.",
        backendUrl,
      },
      { status: 502 },
    );
  }

  // Relay whatever the backend returned — status code and body.
  const contentType = upstream.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  }

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": contentType || "text/plain" },
  });
}
