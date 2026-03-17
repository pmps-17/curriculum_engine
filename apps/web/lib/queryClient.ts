import { QueryClient } from "@tanstack/react-query";

let browserQueryClient: QueryClient | undefined;

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        refetchOnWindowFocus: false,
      },
    },
  });
}

/**
 * Singleton QueryClient.
 * On the server a new client is created per request (no shared state).
 * In the browser the same instance is reused across renders.
 */
export function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    // Server – always fresh
    return makeQueryClient();
  }
  // Browser – singleton
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}
