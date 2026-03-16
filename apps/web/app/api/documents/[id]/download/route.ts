import { NextRequest, NextResponse } from "next/server";
import { endpoints } from "@/lib/config";
import { getBackendAuthHeaders } from "@/lib/auth";

/**
 * GET /api/documents/:id/download
 *
 * Proxies to GET /api/v1/documents/:id/download on the backend.
 * Streams binary content and preserves Content-Type / Content-Disposition.
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const authHeaders = await getBackendAuthHeaders();

  if (!Object.keys(authHeaders).length) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(endpoints.documentDownload(id), {
      method: "GET",
      headers: authHeaders,
      signal: AbortSignal.timeout(60_000),
    });
  } catch (err) {
    console.error("[documents/download] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  if (!upstream.ok) {
    const body = await upstream.json().catch(() => null);
    return NextResponse.json(body, { status: upstream.status });
  }

  // Stream the file bytes through to the client
  const responseHeaders = new Headers();
  const ct = upstream.headers.get("content-type");
  if (ct) responseHeaders.set("Content-Type", ct);
  const cd = upstream.headers.get("content-disposition");
  if (cd) responseHeaders.set("Content-Disposition", cd);
  const cl = upstream.headers.get("content-length");
  if (cl) responseHeaders.set("Content-Length", cl);

  return new NextResponse(upstream.body, {
    status: 200,
    headers: responseHeaders,
  });
}
