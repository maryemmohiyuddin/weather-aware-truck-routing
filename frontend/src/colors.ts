import type { RiskName } from "./types";

export const ROUTE_COLORS: Record<string, string> = {
  A: "#1d4e89",
  B: "#c2410c",
  C: "#0f766e",
};

export const RISK_COLORS: Record<RiskName, string> = {
  low: "#1f7a4d",
  moderate: "#a16207",
  high: "#c2410c",
  severe: "#b42318",
  no_travel: "#5b2c83",
};

export function routeColor(id: string): string {
  return ROUTE_COLORS[id] ?? "#3f3a33";
}
