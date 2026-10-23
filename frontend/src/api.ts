import type { Place, Plan, PlanRequest } from "./types";

// Empty means same origin: /api on this host. The dev server proxies that to Django.
const API_URL = (import.meta.env.VITE_API_URL ?? "").trim().replace(/\/$/, "");

export function apiOrigin(): string {
  return API_URL;
}

export async function searchPlaces(query: string, signal?: AbortSignal): Promise<Place[]> {
  const response = await fetch(`${API_URL}/api/geocode/?q=${encodeURIComponent(query)}`, { signal });
  const body = (await response.json()) as { results?: Place[]; error?: string };
  if (!response.ok) {
    throw new Error(body.error || "Place search failed.");
  }
  return body.results ?? [];
}

export async function requestPlan(plan: PlanRequest, signal?: AbortSignal): Promise<Plan> {
  const response = await fetch(`${API_URL}/api/plan/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(plan),
    signal,
  });
  const body = (await response.json()) as Plan & { error?: string };
  if (!response.ok) {
    throw new Error(body.error || "Could not build routes.");
  }
  return body;
}
