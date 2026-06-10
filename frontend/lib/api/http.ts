/**
 * Unified HTTP fetch helpers (fixes #6 frontend fetch duplication).
 *
 * All API modules were repeating the same !response.ok error handling and
 * response.json() boilerplate. This module extracts that pattern so each
 * API function shrinks to a single fetchJson/postJson/fetchText call. On a
 * non-OK response it surfaces the FastAPI ``{detail}`` message when present,
 * falling back to a generic status message otherwise.
 */

async function throwForStatus(response: Response): Promise<never> {
  let detail = `Request failed with status ${response.status}`;
  try {
    const body = await response.json();
    if (body && typeof body.detail === "string" && body.detail) {
      detail = body.detail;
    }
  } catch {
    // Non-JSON / bodyless response; keep the generic status message.
  }
  throw new Error(detail);
}

export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    await throwForStatus(response);
  }
  return response.json();
}

export async function postJson<T>(url: string, body: unknown): Promise<T> {
  return fetchJson<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function fetchText(url: string, init?: RequestInit): Promise<string> {
  const response = await fetch(url, init);
  if (!response.ok) {
    await throwForStatus(response);
  }
  return response.text();
}
