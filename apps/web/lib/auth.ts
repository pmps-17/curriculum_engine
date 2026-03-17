import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: "select_account",
          access_type: "offline",
        },
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
  callbacks: {
    /** Persist the Google id_token inside the NextAuth JWT. */
    async jwt({ token, account }) {
      // `account` is only available on the initial sign-in
      if (account?.id_token) {
        token.id_token = account.id_token;
      }
      return token;
    },

    /** Expose the id_token on the client-visible session. */
    async session({ session, token }) {
      (session as any).id_token = token.id_token as string | undefined;
      return session;
    },

    authorized({ auth: session, request }) {
      const { pathname } = request.nextUrl;

      // Public routes
      if (
        pathname.startsWith("/login") ||
        pathname.startsWith("/api/auth")
      ) {
        return true;
      }

      // Everything else requires a session
      return !!session?.user;
    },
  },
});

/* ------------------------------------------------------------------ */
/*  Server-side helpers for proxy route handlers                      */
/* ------------------------------------------------------------------ */

/**
 * Read the authenticated user's email from the NextAuth session.
 *
 * Call this inside Next.js route handlers (server-side only) to get
 * the trusted email for forwarding to the backend as X-User-Email.
 *
 * Returns `null` if no valid session exists.
 */
export async function getSessionEmail(): Promise<string | null> {
  const session = await auth();
  return session?.user?.email ?? null;
}

/**
 * Read the Google ID token from the NextAuth session.
 *
 * This is the raw JWT issued by Google during sign-in. The backend
 * verifies it cryptographically when AUTH_MODE=google_jwt.
 *
 * Returns `null` if no session or the token was not persisted.
 */
export async function getSessionIdToken(): Promise<string | null> {
  const session = await auth();
  return (session as any)?.id_token ?? null;
}

/**
 * Build auth headers for proxying requests to the FastAPI backend.
 *
 * Returns both `Authorization: Bearer <id_token>` (for google_jwt mode)
 * and `X-User-Email` (for dev_header mode) so the backend works in
 * either AUTH_MODE without frontend changes.
 */
export async function getBackendAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  const session = await auth();
  if (!session?.user?.email) return headers;

  headers["X-User-Email"] = session.user.email;

  const idToken = (session as any)?.id_token;
  if (idToken) {
    headers["Authorization"] = `Bearer ${idToken}`;
  }

  return headers;
}
