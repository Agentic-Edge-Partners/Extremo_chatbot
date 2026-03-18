const STORAGE_KEY = "lg:chat:apiKey";

/**
 * Retrieves the API key from localStorage, falling back to the
 * NEXT_PUBLIC_LANGSMITH_API_KEY environment variable.
 */
export function getApiKey(): string | null {
  if (typeof window !== "undefined") {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
  }

  return process.env.NEXT_PUBLIC_LANGSMITH_API_KEY ?? null;
}
