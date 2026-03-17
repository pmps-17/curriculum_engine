import { z } from "zod";

/* ------------------------------------------------------------------ */
/*  Analyze request                                                   */
/* ------------------------------------------------------------------ */

export const AnalyzeRequestSchema = z
  .object({
    title: z.string().min(1, "Title is required"),
    subject: z.string().min(1, "Subject is required"),
    grade_band: z.string().min(1, "Grade band is required"),
    curriculum_text: z.string().optional(),
    document_id: z.string().uuid().optional(),
    rubric_text: z.string().optional(),
  })
  .refine(
    (d) =>
      (d.curriculum_text && d.curriculum_text.length >= 20) ||
      (d.document_id && d.document_id.length > 0),
    {
      message:
        "Provide curriculum text (min 20 chars) or upload a document",
      path: ["curriculum_text"],
    },
  );

export type AnalyzeRequest = z.infer<typeof AnalyzeRequestSchema>;
