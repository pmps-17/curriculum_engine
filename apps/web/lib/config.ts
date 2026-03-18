/**
 * Base URL of the Python backend (used server-side in route handlers).
 *
 * Read from NEXT_PUBLIC_API_BASE_URL.  Falls back to localhost for dev.
 * A clear error is thrown at import-time if the value is explicitly empty
 * so misconfigured deployments fail fast.
 */
const raw = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

if (raw === "") {
  throw new Error(
    "[config] NEXT_PUBLIC_API_BASE_URL is set but empty. " +
      "Set it to the backend origin, e.g. http://127.0.0.1:8000",
  );
}

export const API_BASE_URL: string = raw ?? "http://127.0.0.1:8000";

/* ------------------------------------------------------------------ */
/*  Endpoint builders (server-side – point at the real backend)       */
/* ------------------------------------------------------------------ */

export const endpoints = {
  analyze: () => `${API_BASE_URL}/api/v1/analyze`,
  health: () => `${API_BASE_URL}/health`,
  results: (id: string) => `${API_BASE_URL}/api/v1/results/${id}`,
  uploads: () => `${API_BASE_URL}/api/v1/uploads`,
  documentMeta: (id: string) => `${API_BASE_URL}/api/v1/documents/${id}`,
  documentPreview: (id: string) => `${API_BASE_URL}/api/v1/documents/${id}/preview`,
  documentDownload: (id: string) => `${API_BASE_URL}/api/v1/documents/${id}/download`,
} as const;

/* ------------------------------------------------------------------ */
/*  Proxy paths (client-side – point at Next.js route handlers)       */
/* ------------------------------------------------------------------ */

export const proxyPaths = {
  analyze: "/api/analyze",
  backendHealth: "/api/backend-health",
  results: (id: string) => `/api/results/${id}`,
  uploads: "/api/uploads",
  documentPreview: (id: string) => `/api/documents/${id}/preview`,
  documentDownload: (id: string) => `/api/documents/${id}/download`,
  organizations: "/api/organizations",
  organizationPatch: (id: string) => `/api/organizations/${id}`,
  organizationLeave: (id: string) => `/api/organizations/${id}/leave`,
  curriculumSets: "/api/curriculum-sets",
  curriculumSetDetail: (id: string) => `/api/curriculum-sets/${id}`,
} as const;
