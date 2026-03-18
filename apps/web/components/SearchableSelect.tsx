"use client";

import { useEffect, useRef, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

export interface SelectOption {
  label: string;
  value: string;
}

interface SearchableSelectProps {
  options: SelectOption[];
  value: string;                       // currently-selected value
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

/* ------------------------------------------------------------------ */
/*  Shared input style (matches the rest of the app)                  */
/* ------------------------------------------------------------------ */

const INPUT =
  "h-10 w-full rounded-lg border border-gray-200 bg-white px-3.5 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20";

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = "Select…",
  disabled = false,
  className = "",
}: SearchableSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  /* Resolve the display label for the current value */
  const selectedLabel = options.find((o) => o.value === value)?.label ?? "";

  /* ── Filtered options ──────────────────────────────────────────── */
  const needle = search.toLowerCase();
  const filtered = search
    ? options.filter((o) => o.label.toLowerCase().includes(needle))
    : options;

  /* ── Close on outside click ────────────────────────────────────── */
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  /* ── Open the dropdown ─────────────────────────────────────────── */
  function handleOpen() {
    if (disabled) return;
    setOpen(true);
    setSearch("");
    // Focus the search input after paint
    requestAnimationFrame(() => inputRef.current?.focus());
  }

  /* ── Pick an option ────────────────────────────────────────────── */
  function handleSelect(opt: SelectOption) {
    onChange(opt.value);
    setOpen(false);
    setSearch("");
  }

  /* ── Clear ─────────────────────────────────────────────────────── */
  function handleClear(e: React.MouseEvent) {
    e.stopPropagation();
    onChange("");
    setOpen(false);
    setSearch("");
  }

  /* ── Keyboard ──────────────────────────────────────────────────── */
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Trigger button */}
      <button
        type="button"
        onClick={handleOpen}
        disabled={disabled}
        className={`${INPUT} flex items-center justify-between gap-2 text-left ${
          disabled ? "cursor-not-allowed bg-gray-50 text-gray-400" : "cursor-pointer"
        }`}
      >
        <span className={selectedLabel ? "text-gray-900" : "text-gray-400"}>
          {selectedLabel || placeholder}
        </span>
        <span className="flex shrink-0 items-center gap-1">
          {value && !disabled && (
            <span
              role="button"
              tabIndex={-1}
              onClick={handleClear}
              className="rounded p-0.5 text-gray-400 hover:text-gray-600"
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </span>
          )}
          <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg">
          {/* Search box */}
          <div className="border-b border-gray-100 px-3 py-2">
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search…"
              className="h-8 w-full rounded-md border border-gray-200 bg-gray-50 px-3 text-sm outline-none placeholder:text-gray-400 focus:border-[#4F46E5] focus:ring-1 focus:ring-[#4F46E5]/20"
            />
          </div>

          {/* Options list */}
          <ul
            ref={listRef}
            className="max-h-52 overflow-y-auto overscroll-contain py-1"
          >
            {filtered.length === 0 && (
              <li className="px-3.5 py-2.5 text-xs text-gray-400">
                No matches
              </li>
            )}
            {filtered.map((opt) => {
              const active = opt.value === value;
              return (
                <li
                  key={opt.value}
                  role="option"
                  aria-selected={active}
                  onClick={() => handleSelect(opt)}
                  className={`cursor-pointer px-3.5 py-2 text-sm transition ${
                    active
                      ? "bg-[#4F46E5]/5 font-medium text-[#4F46E5]"
                      : "text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {opt.label}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
