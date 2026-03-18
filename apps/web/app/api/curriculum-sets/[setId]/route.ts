import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL } from "@/lib/config";
import { getSessionEmail, getBackendAuthHeaders } from "@/lib/auth";

/**
 * GET    /api/curriculum-sets/[setId]  → backend GET  (not used yet, placeholder)
 * PATCH  /api/curriculum-sets/[setId]  → backend PATCH /api/v1/curriculum-sets/{setId}
 * DELETE /api/curriculum-sets/[setId]  → backend DELETE /api/v1/curriculum-sets/{setId}
 */

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ setId: string }> },
): Promise<NextResponse> {
  const { setId } = await params;
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

  const backendUrl = `${API_BASE_URL}/api/v1/curriculum-sets/${setId}`;
  const authHeaders = await getBackendAuthHeaders();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10_000),
    });
  } catch (err) {
    console.error("[curriculum-sets/patch] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ setId: string }> },
): Promise<NextResponse> {
  const { setId } = await params;
  const email = await getSessionEmail();
  if (!email) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const backendUrl = `${API_BASE_URL}/api/v1/curriculum-sets/${setId}`;
  const authHeaders = await getBackendAuthHeaders();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, {
      method: "DELETE",
      headers: { ...authHeaders },
      signal: AbortSignal.timeout(10_000),
    });
  } catch (err) {
    console.error("[curriculum-sets/delete] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  if (upstream.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}
