import type { RiskName } from "./types";

export function formatMiles(miles: number): string {
  return `${miles.toFixed(1)} mi`;
}

export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours <= 0) return `${mins} min`;
  if (mins === 0) return `${hours} h`;
  return `${hours} h ${mins} min`;
}

export function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatLeaving(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "the selected hour";
  return date.toLocaleString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** "Wed 7 AM" for the slider readout. */
export function formatHourClock(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "the selected hour";
  const day = date.toLocaleString(undefined, { weekday: "short" });
  const hour = date.toLocaleString(undefined, { hour: "numeric" });
  return `${day} ${hour}`;
}

/** "Thursday 1 AM" for the best-departure hint. */
export function formatBestLeave(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "the selected hour";
  const day = date.toLocaleString(undefined, { weekday: "long" });
  const hour = date.toLocaleString(undefined, { hour: "numeric" });
  return `${day} ${hour}`;
}

export function riskLabel(risk: RiskName): string {
  if (risk === "no_travel") return "No travel";
  return risk.charAt(0).toUpperCase() + risk.slice(1);
}

export function defaultDepartureValue(now = new Date()): string {
  const date = new Date(now);
  const alreadyOnTheHour =
    date.getMinutes() === 0 && date.getSeconds() === 0 && date.getMilliseconds() === 0;
  date.setMinutes(0, 0, 0);
  if (!alreadyOnTheHour) {
    date.setHours(date.getHours() + 1);
  }
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function localInputToIso(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new Error("Choose a valid departure time.");
  }
  return date.toISOString();
}
