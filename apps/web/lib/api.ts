export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(`API error ${status}`);
    this.name = "ApiError";
  }
}

interface FetchOptions<TBody = unknown> extends Omit<RequestInit, "body"> {
  body?: TBody;
}

/**
 * Typed fetch wrapper that targets the Next.js proxy routes.
 *
 * - Automatically serialises JSON bodies.
 * - Auth is handled server-side by proxy routes (NextAuth session).
 * - Throws `ApiError` on non-2xx responses.
 * - Returns the parsed JSON typed as `TResponse`.
 */
export async function apiFetch<TResponse, TBody = unknown>(
  path: string,
  { body, headers, ...rest }: FetchOptions<TBody> = {},
): Promise<TResponse> {
  const res = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    ...(body !== undefined && { body: JSON.stringify(body) }),
    ...rest,
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => null);
    throw new ApiError(res.status, errorBody);
  }

  return res.json() as Promise<TResponse>;
}
