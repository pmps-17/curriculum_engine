"use client";

import { useState, useEffect, useMemo } from "react";
import { Country, State, ICountry, IState } from "country-state-city";
import SearchableSelect, { type SelectOption } from "@/components/SearchableSelect";

/* ------------------------------------------------------------------ */
/*  Props                                                             */
/* ------------------------------------------------------------------ */

interface EditOrganizationModalProps {
  open: boolean;
  organizationId: string;
  initialName: string;
  initialDescription: string;
  initialContactName?: string;
  initialContactEmail?: string;
  initialCountryCode?: string;
  initialStateCode?: string;
  initialStateName?: string;
  initialCity?: string;
  onClose: () => void;
  onSaved: (updated: { name: string; description: string | null }) => void;
}

/* ------------------------------------------------------------------ */
/*  Shared style                                                      */
/* ------------------------------------------------------------------ */

const INPUT =
  "h-10 w-full rounded-lg border border-gray-200 bg-white px-3.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20";

const LABEL = "text-xs font-medium text-gray-600";

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function EditOrganizationModal({
  open,
  organizationId,
  initialName,
  initialDescription,
  initialContactName = "",
  initialContactEmail = "",
  initialCountryCode = "",
  initialStateCode = "",
  initialStateName = "",
  initialCity = "",
  onClose,
  onSaved,
}: EditOrganizationModalProps) {
  /* ── Core fields ───────────────────────────────────────────────── */
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  const [contactName, setContactName] = useState(initialContactName);
  const [contactEmail, setContactEmail] = useState(initialContactEmail);

  /* ── Location ──────────────────────────────────────────────────── */
  const [countryCode, setCountryCode] = useState(initialCountryCode);
  const [stateCode, setStateCode] = useState(initialStateCode);
  const [stateNameTyped, setStateNameTyped] = useState(initialStateName);
  const [city, setCity] = useState(initialCity);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  /* ── Sync when modal reopens ───────────────────────────────────── */
  useEffect(() => {
    if (open) {
      setName(initialName);
      setDescription(initialDescription);
      setContactName(initialContactName);
      setContactEmail(initialContactEmail);
      setCountryCode(initialCountryCode);
      setStateCode(initialStateCode);
      setStateNameTyped(initialStateName);
      setCity(initialCity);
      setError("");
    }
  }, [
    open, initialName, initialDescription,
    initialContactName, initialContactEmail,
    initialCountryCode, initialStateCode, initialStateName, initialCity,
  ]);

  /* ── Derived data ──────────────────────────────────────────────── */

  const countryOptions: SelectOption[] = useMemo(
    () =>
      Country.getAllCountries().map((c: ICountry) => ({
        label: c.name,
        value: c.isoCode,
      })),
    [],
  );

  const stateOptions: SelectOption[] = useMemo(() => {
    if (!countryCode) return [];
    return State.getStatesOfCountry(countryCode).map((s: IState) => ({
      label: s.name,
      value: s.isoCode,
    }));
  }, [countryCode]);

  const hasStates = stateOptions.length > 0;

  const selectedCountry = countryCode
    ? Country.getCountryByCode(countryCode)
    : null;
  const selectedState =
    countryCode && stateCode && hasStates
      ? State.getStateByCodeAndCountry(stateCode, countryCode)
      : null;

  if (!open) return null;

  /* ── Country change resets dependent fields ────────────────────── */
  function handleCountryChange(val: string) {
    setCountryCode(val);
    setStateCode("");
    setStateNameTyped("");
    setCity("");
    setError("");
  }

  /* ── Submit ────────────────────────────────────────────────────── */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Name cannot be empty.");
      return;
    }
    setLoading(true);
    setError("");

    const payload: Record<string, string | null> = {
      name: name.trim(),
      description: description.trim() || null,
      contact_name: contactName.trim() || null,
      contact_email: contactEmail.trim() || null,
      country_name: selectedCountry?.name ?? null,
      country_code: selectedCountry?.isoCode ?? null,
      state_name: hasStates
        ? (selectedState?.name ?? null)
        : (stateNameTyped.trim() || null),
      state_code: hasStates
        ? (selectedState?.isoCode ?? null)
        : (stateNameTyped.trim() || null),
      city: city.trim() || null,
    };

    try {
      const res = await fetch(`/api/organizations/${organizationId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => null);
        throw new Error(b?.detail ?? `Error ${res.status}`);
      }
      const org = await res.json();
      onSaved({ name: org.name, description: org.description ?? "" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setLoading(false);
    }
  }

  function handleBackdrop(e: React.MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
      onClick={handleBackdrop}
    >
      <div className="w-full max-w-lg rounded-2xl border border-gray-200/80 bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-bold text-gray-900">Edit Organization</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="max-h-[70vh] overflow-y-auto px-6 py-5 space-y-5">
          {/* ── Name + Description ─────────────────────────────────── */}
          <div className="space-y-3">
            <div className="flex flex-col gap-1">
              <label className={LABEL}>Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => { setName(e.target.value); setError(""); }}
                className={INPUT}
                autoFocus
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className={LABEL}>Description <span className="text-gray-400">(optional)</span></label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Short description of the organization…"
                className="w-full rounded-lg border border-gray-200 bg-white px-3.5 py-2.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20 resize-none"
              />
            </div>
          </div>

          {/* ── Contact ────────────────────────────────────────────── */}
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Contact</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className={LABEL}>Contact Name</label>
                <input
                  type="text"
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  placeholder="Jane Doe"
                  className={INPUT}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className={LABEL}>Contact Email</label>
                <input
                  type="email"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  placeholder="jane@example.com"
                  className={INPUT}
                />
              </div>
            </div>
          </div>

          {/* ── Location ───────────────────────────────────────────── */}
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Location</p>

            <div className="flex flex-col gap-1">
              <label className={LABEL}>Country</label>
              <SearchableSelect
                options={countryOptions}
                value={countryCode}
                onChange={handleCountryChange}
                placeholder="Select country…"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className={LABEL}>State / Region</label>
                {hasStates ? (
                  <SearchableSelect
                    options={stateOptions}
                    value={stateCode}
                    onChange={(v) => { setStateCode(v); setError(""); }}
                    placeholder="Select state…"
                    disabled={!countryCode}
                  />
                ) : (
                  <input
                    type="text"
                    value={stateNameTyped}
                    onChange={(e) => setStateNameTyped(e.target.value)}
                    placeholder={countryCode ? "Type state/region…" : "Select country first"}
                    disabled={!countryCode}
                    className={`${INPUT} ${!countryCode ? "cursor-not-allowed bg-gray-50 text-gray-400" : ""}`}
                  />
                )}
              </div>
              <div className="flex flex-col gap-1">
                <label className={LABEL}>City</label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="City name"
                  className={INPUT}
                />
              </div>
            </div>
          </div>

          {/* ── Error + Actions ─────────────────────────────────────── */}
          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="h-9 rounded-lg px-4 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="h-9 rounded-lg bg-[#4F46E5] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#4338CA] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
