import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL } from "@/lib/config";
import { getSessionEmail, getBackendAuthHeaders } from "@/lib/auth";

/**
 * GET  /api/curriculum-sets?organization_id=…  → backend GET /api/v1/curriculum-sets?organization_id=…
 * POST /api/curriculum-sets                    → backend POST /api/v1/curriculum-sets
 */

export async function GET(req: NextRequest): Promise<NextResponse> {
  const email = await getSessionEmail();
  if (!email) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const orgId = req.nextUrl.searchParams.get("organization_id");
  if (!orgId) {
    return NextResponse.json({ detail: "organization_id is required." }, { status: 400 });
  }

  const backendUrl = `${API_BASE_URL}/api/v1/curriculum-sets?organization_id=${encodeURIComponent(orgId)}`;
  const authHeaders = await getBackendAuthHeaders();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, {
      method: "GET",
      headers: { Accept: "application/json", ...authHeaders },
      signal: AbortSignal.timeout(10_000),
    });
  } catch (err) {
    console.error("[curriculum-sets] Backend unreachable:", err);
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

  const backendUrl = `${API_BASE_URL}/api/v1/curriculum-sets`;
  const authHeaders = await getBackendAuthHeaders();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10_000),
    });
  } catch (err) {
    console.error("[curriculum-sets] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}
