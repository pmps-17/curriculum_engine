import { NextRequest, NextResponse } from "next/server";
import { endpoints } from "@/lib/config";
import { getSessionEmail, getBackendAuthHeaders } from "@/lib/auth";

/**
 * POST /api/analyze
 *
 * Proxies JSON requests to the FastAPI backend at /api/v1/analyze.
 *
 * - Reads email from the NextAuth session (server-side).
 * - Preserves the backend's status code (including 4xx / 5xx).
 * - Returns a structured 502 when the backend is unreachable.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const backendUrl = endpoints.analyze();

  // 0. Authenticate via session
  const email = await getSessionEmail();
  if (!email) {
    return NextResponse.json(
      { error: "Not authenticated." },
      { status: 401 },
    );
  }

  // 1. Parse the JSON body from the browser
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "INVALID_JSON", detail: "Request body is not valid JSON." },
      { status: 400 },
    );
  }

  // 2. Forward to the FastAPI backend
  let upstream: Response;
  try {
    const authHeaders = await getBackendAuthHeaders();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...authHeaders,
    };

    upstream = await fetch(backendUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  } catch (err) {
    console.error("[analyze] Backend unreachable:", err);
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

  // 3. Relay the backend response transparently (including 4xx/5xx)
  const contentType = upstream.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  }

  // Non-JSON response (unexpected) — relay as text
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": contentType || "text/plain" },
  });
}
