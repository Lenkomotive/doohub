const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = typeof window !== "undefined"
    ? sessionStorage.getItem("access_token")
    : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401 && token) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${sessionStorage.getItem("access_token")}`;
      return fetch(`${API_URL}${path}`, { ...options, headers });
    }
  }

  return res;
}

export async function apiUpload(
  path: string,
  body: FormData,
): Promise<Response> {
  const token = typeof window !== "undefined"
    ? sessionStorage.getItem("access_token")
    : null;

  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers,
    body,
  });

  if (res.status === 401 && token) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${sessionStorage.getItem("access_token")}`;
      return fetch(`${API_URL}${path}`, { method: "POST", headers, body });
    }
  }

  return res;
}

async function tryRefresh(): Promise<boolean> {
  const refreshToken = sessionStorage.getItem("refresh_token");
  if (!refreshToken) return false;

  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!res.ok) {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
    return false;
  }

  const data = await res.json();
  sessionStorage.setItem("access_token", data.access_token);
  sessionStorage.setItem("refresh_token", data.refresh_token);
  return true;
}
