import { NextRequest, NextResponse } from "next/server";
import { endpoints } from "@/lib/config";
import { getBackendAuthHeaders } from "@/lib/auth";

type RouteCtx = { params: Promise<{ id: string }> };

/**
 * GET /api/documents/:id
 *
 * Proxies to GET /api/v1/documents/:id on the backend (metadata only).
 */
export async function GET(_req: NextRequest, { params }: RouteCtx) {
  const { id } = await params;
  const authHeaders = await getBackendAuthHeaders();

  if (!Object.keys(authHeaders).length) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(endpoints.documentMeta(id), {
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

/**
 * PATCH /api/documents/:id
 *
 * Proxies to PATCH /api/v1/documents/:id on the backend.
 */
export async function PATCH(req: NextRequest, { params }: RouteCtx) {
  const { id } = await params;
  const authHeaders = await getBackendAuthHeaders();

  if (!Object.keys(authHeaders).length) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON." }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(endpoints.documentMeta(id), {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10_000),
    });
  } catch (err) {
    console.error("[documents] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}

/**
 * DELETE /api/documents/:id
 *
 * Proxies to DELETE /api/v1/documents/:id on the backend.
 */
export async function DELETE(_req: NextRequest, { params }: RouteCtx) {
  const { id } = await params;
  const authHeaders = await getBackendAuthHeaders();

  if (!Object.keys(authHeaders).length) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(endpoints.documentMeta(id), {
      method: "DELETE",
      headers: { ...authHeaders },
      signal: AbortSignal.timeout(10_000),
    });
  } catch (err) {
    console.error("[documents] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  if (upstream.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}
