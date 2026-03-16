"use client";

import { useSession, signOut } from "next-auth/react";

export default function UserNav() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <div className="h-8 w-24 animate-pulse rounded-md bg-gray-100" />
    );
  }

  if (!session?.user) return null;

  const name = session.user.name ?? session.user.email ?? "User";
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="flex items-center gap-3">
      {/* Avatar circle */}
      {session.user.image ? (
        <img
          src={session.user.image}
          alt={name}
          className="h-7 w-7 rounded-full ring-1 ring-gray-200"
          referrerPolicy="no-referrer"
        />
      ) : (
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#4F46E5]/10 text-xs font-semibold text-[#4F46E5]">
          {initials}
        </span>
      )}

      {/* Name / email */}
      <span className="hidden text-sm text-gray-600 sm:inline">
        {name}
      </span>

      {/* Sign out */}
      <button
        type="button"
        onClick={() => signOut({ callbackUrl: "/login" })}
        className="rounded-md border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-500 transition hover:bg-gray-50 hover:text-gray-700"
      >
        Sign out
      </button>
    </div>
  );
}
