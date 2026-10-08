// Access token storage. sessionStorage: survives a page refresh, cleared when the tab closes.
// Trade-offs are explained in the README ("Token storage").
const KEY = "ls_access_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(KEY);
}

export function setToken(token: string): void {
  window.sessionStorage.setItem(KEY, token);
}

export function clearToken(): void {
  window.sessionStorage.removeItem(KEY);
}
