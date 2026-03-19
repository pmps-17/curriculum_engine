import { useMutation } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";
import { uploadDocument, type UploadResponse } from "@/lib/documents";

export type { UploadResponse };

/* ------------------------------------------------------------------ */
/*  Upload mutation                                                   */
/* ------------------------------------------------------------------ */

/**
 * React-Query mutation that wraps {@link uploadDocument}.
 *
 * Accepts a `FormData` with a `file` entry (and optionally
 * `title`, `subject`, `grade_band`).  The `organization_id` is
 * read from `localStorage` and injected automatically.
 */
export function useUploadMutation() {
  return useMutation<UploadResponse, ApiError, FormData>({
    mutationFn: async (formData) => {
      const orgId =
        typeof window !== "undefined"
          ? localStorage.getItem("organization_id") ?? ""
          : "";

      const file = formData.get("file") as File | null;
      if (!file) throw new ApiError(400, { detail: "No file provided." });

      return uploadDocument(orgId, file, {
        title: (formData.get("title") as string) || undefined,
        subject: (formData.get("subject") as string) || undefined,
        grade_band: (formData.get("grade_band") as string) || undefined,
      });
    },
  });
}
