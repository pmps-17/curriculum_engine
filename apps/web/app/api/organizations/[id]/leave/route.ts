import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL } from "@/lib/config";
import { getSessionEmail, getBackendAuthHeaders } from "@/lib/auth";

/**
 * POST /api/organizations/[id]/leave → backend POST /api/v1/organizations/{id}/leave
 */
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await params;
  const email = await getSessionEmail();
  if (!email) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const backendUrl = `${API_BASE_URL}/api/v1/organizations/${id}/leave`;
  const authHeaders = await getBackendAuthHeaders();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
      },
      signal: AbortSignal.timeout(10_000),
    });
  } catch (err) {
    console.error("[organizations/leave] Backend unreachable:", err);
    return NextResponse.json({ error: "BACKEND_UNREACHABLE" }, { status: 502 });
  }

  // 204 has no body
  if (upstream.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}
