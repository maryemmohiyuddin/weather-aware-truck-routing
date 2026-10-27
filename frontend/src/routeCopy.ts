import type { RiskName } from "./types";

const CLASSES: RiskName[] = ["low", "moderate", "high", "severe", "no_travel"];

/** 1.00 is Low. The word follows the same 1–5 scores the server already uses. */
export function averageRiskClass(average: number): RiskName {
  const score = Math.min(5, Math.max(1, Math.round(average)));
  return CLASSES[score - 1];
}

function mileCount(miles: number): string {
  const rounded = Math.round(miles * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

/** Plain sentence for the route card. Moderate miles are not called risky here. */
export function stretchSummary(miles: { no_travel: number; severe: number; high: number }): string {
  const parts: string[] = [];
  if (miles.no_travel > 0) parts.push(`${mileCount(miles.no_travel)} mi no-travel`);
  if (miles.severe > 0) parts.push(`${mileCount(miles.severe)} mi severe`);
  if (miles.high > 0) parts.push(`${mileCount(miles.high)} mi high`);
  if (!parts.length) return "No risky stretches on this route";
  return parts.join(", ");
}

/** Changes when the sample spacing changes, so the map remounts those dots. */
export function stopsLayerKey(routeId: string, sampleMiles: number, stopCount: number): string {
  return `${routeId}-${sampleMiles}-${stopCount}`;
}
