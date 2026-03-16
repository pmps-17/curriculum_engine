import { useMutation } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";
import { proxyPaths } from "@/lib/config";

/* ------------------------------------------------------------------ */
/*  Response type                                                     */
/* ------------------------------------------------------------------ */

export interface UploadResponse {
  document_id: string;
  filename: string;
  content_type?: string;
  size_bytes?: number;
  extraction_status: "EXTRACTED" | "STORED_ONLY" | "REJECTED";
  warnings?: string[];
  preview_text?: string | null;
  preview_truncated?: boolean | null;
}

/* ------------------------------------------------------------------ */
/*  Upload mutation                                                   */
/* ------------------------------------------------------------------ */

export function useUploadMutation() {
  return useMutation<UploadResponse, ApiError, FormData>({
    mutationFn: async (formData) => {
      // Inject workspace_id for tenancy
      const wsId =
        typeof window !== "undefined"
          ? localStorage.getItem("workspace_id") ?? ""
          : "";

      if (wsId) formData.append("workspace_id", wsId);

      const res = await fetch(proxyPaths.uploads, {
        method: "POST",
        // Do NOT set Content-Type — browser will add the correct
        // multipart boundary automatically.
        // Auth is handled server-side by the proxy route (NextAuth session).
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new ApiError(res.status, body);
      }

      return res.json() as Promise<UploadResponse>;
    },
  });
}
