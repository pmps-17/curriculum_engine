"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

export interface DocumentActionsMenuProps {
  hasReport: boolean;
  onRunAnalysis: () => void;
  onViewReport: () => void;
  onRename: () => void;
  onDelete: () => void;
}

/* ------------------------------------------------------------------ */
/*  Three-dot icon                                                    */
/* ------------------------------------------------------------------ */

function DotsIcon() {
  return (
    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
      <path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function DocumentActionsMenu({
  hasReport,
  onRunAnalysis,
  onViewReport,
  onRename,
  onDelete,
}: DocumentActionsMenuProps) {
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });

  /* Position the portal-rendered menu below the button */
  useEffect(() => {
    if (!open || !btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    setPos({ top: rect.bottom + 4, left: rect.right - 176 }); // 176 = w-44
  }, [open]);

  /* Close on outside click */
  useEffect(() => {
    if (!open) return;
    function handle(e: MouseEvent) {
      const target = e.target as Node;
      if (
        btnRef.current && !btnRef.current.contains(target) &&
        menuRef.current && !menuRef.current.contains(target)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [open]);

  /* Close on scroll (table may scroll underneath) */
  useEffect(() => {
    if (!open) return;
    function handle() { setOpen(false); }
    window.addEventListener("scroll", handle, true);
    return () => window.removeEventListener("scroll", handle, true);
  }, [open]);

  function item(label: string, onClick: () => void, danger = false) {
    return (
      <button
        type="button"
        data-row-action
        onClick={(e) => {
          e.stopPropagation();
          setOpen(false);
          onClick();
        }}
        className={`w-full px-3.5 py-2 text-left text-sm transition ${
          danger
            ? "text-red-600 hover:bg-red-50"
            : "text-gray-700 hover:bg-gray-50"
        }`}
      >
        {label}
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        ref={btnRef}
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
        aria-label="Document actions"
      >
        <DotsIcon />
      </button>

      {open &&
        createPortal(
          <div
            ref={menuRef}
            data-row-action
            style={{ position: "fixed", top: pos.top, left: pos.left }}
            className="z-[9999] w-44 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg"
          >
            {hasReport && item("View Report", onViewReport)}
            {item("Run Analysis", onRunAnalysis)}
            {item("Edit", onRename)}
            <div className="border-t border-gray-100" />
            {item("Delete", onDelete, true)}
          </div>,
          document.body,
        )}
    </div>
  );
}
