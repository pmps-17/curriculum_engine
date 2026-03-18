/**
 * Centralized organization-selection state.
 *
 * Stores `organization_id` and `organization_name` in localStorage.
 * All UI code should use these helpers — there is no second copy.
 */

/* ── Getters ─────────────────────────────────────────────────────── */

export function getOrgId(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("organization_id") ?? "";
}

export function getOrgName(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("organization_name") ?? "";
}

/* ── Setters ─────────────────────────────────────────────────────── */

export function setOrg(id: string, name: string): void {
  localStorage.setItem("organization_id", id);
  localStorage.setItem("organization_name", name);
  // Dispatch a storage event so other tabs / components react
  window.dispatchEvent(new StorageEvent("storage", { key: "organization_name", newValue: name }));
}

export function clearOrg(): void {
  localStorage.removeItem("organization_id");
  localStorage.removeItem("organization_name");
  window.dispatchEvent(new StorageEvent("storage", { key: "organization_name", newValue: "" }));
}
