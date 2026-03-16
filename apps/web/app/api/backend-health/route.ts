import { NextResponse } from "next/server";
import { endpoints, API_BASE_URL } from "@/lib/config";

/**
 * GET /api/backend-health
 *
 * Connectivity check — calls the FastAPI /health endpoint and relays the
 * result.  Useful for debugging 502s from the browser DevTools or CI.
 */
export async function GET(): Promise<NextResponse> {
  const backendUrl = endpoints.health();

  try {
    const upstream = await fetch(backendUrl, {
      method: "GET",
      // Short timeout so the probe is fast
      signal: AbortSignal.timeout(5_000),
    });

    const contentType = upstream.headers.get("content-type") ?? "";
    const body = contentType.includes("application/json")
      ? await upstream.json()
      : await upstream.text();

    return NextResponse.json(
      {
        status: "ok",
        backendUrl: API_BASE_URL,
        backendStatus: upstream.status,
        backendBody: body,
      },
      { status: 200 },
    );
  } catch (err) {
    console.error("[backend-health] Backend unreachable:", err);
    return NextResponse.json(
      {
        status: "unreachable",
        error: "BACKEND_UNREACHABLE",
        detail:
          err instanceof Error ? err.message : "Could not connect to backend.",
        backendUrl: API_BASE_URL,
        hint: `Is the FastAPI server running?  Try: curl ${backendUrl}`,
      },
      { status: 502 },
    );
  }
}
