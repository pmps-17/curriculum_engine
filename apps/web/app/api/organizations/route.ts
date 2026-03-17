import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL } from "@/lib/config";
import { getSessionEmail, getBackendAuthHeaders } from "@/lib/auth";

/**
 * GET  /api/organizations  → backend GET /api/v1/organizations
 * POST /api/organizations  → backend POST /api/v1/organizations
 *
 * Reads email from the NextAuth session (server-side).
 */

export async function GET(req: NextRequest): Promise<NextResponse> {
  const email = await getSessionEmail();
  if (!email) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const backendUrl = `${API_BASE_URL}/api/v1/organizations`;
  const authHeaders = await getBackendAuthHeaders();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...authHeaders,
      },
      signal: AbortSignal.timeout(10_000),
    });
  } catch (err) {
    console.error("[organizations] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const email = await getSessionEmail();
  if (!email) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON." }, { status: 400 });
  }

  const backendUrl = `${API_BASE_URL}/api/v1/organizations`;
  const authHeaders = await getBackendAuthHeaders();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10_000),
    });
  } catch (err) {
    console.error("[organizations] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}
