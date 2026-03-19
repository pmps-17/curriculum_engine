import { NextRequest, NextResponse } from "next/server";
import { endpoints } from "@/lib/config";
import { getBackendAuthHeaders } from "@/lib/auth";

type RouteCtx = { params: Promise<{ id: string }> };

/**
 * PATCH /api/documents/:id/content
 *
 * Proxies multipart/form-data to PATCH /api/v1/documents/:id/content.
 */
export async function PATCH(req: NextRequest, { params }: RouteCtx) {
  const { id } = await params;
  const authHeaders = await getBackendAuthHeaders();

  if (!Object.keys(authHeaders).length) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  // Forward the raw body as-is (multipart/form-data)
  const contentType = req.headers.get("content-type") ?? "";
  const body = await req.arrayBuffer();

  let upstream: Response;
  try {
    upstream = await fetch(endpoints.documentContent(id), {
      method: "PATCH",
      headers: { "Content-Type": contentType, ...authHeaders },
      body,
      signal: AbortSignal.timeout(30_000),
    });
  } catch (err) {
    console.error("[documents/content] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}
