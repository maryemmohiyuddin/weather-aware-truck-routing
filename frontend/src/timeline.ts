import type { Plan } from "./types";

/** Swap in the precomputed hour. Geometry stays; risk, rank, and arrivals change. */
export function planAtHour(plan: Plan, hour: number): Plan {
  const frames = plan.timeline;
  if (!frames?.length) return plan;
  const offset = Math.max(0, Math.min(Math.round(hour), frames.length - 1));
  const frame = frames[offset];
  const byId = new Map(frame.routes.map((route) => [route.id, route]));
  const routes = plan.routes.map((route) => {
    const snap = byId.get(route.id);
    if (!snap) return route;
    return {
      ...route,
      miles: snap.miles,
      average_risk: snap.average_risk,
      rank: snap.rank,
      recommended: snap.recommended,
      checkpoints: route.checkpoints.map((checkpoint, index) => ({
        ...checkpoint,
        ...snap.checkpoints[index],
      })),
    };
  });
  routes.sort((a, b) => a.rank - b.rank);
  return {
    ...plan,
    departure: frame.departure,
    recommendation: frame.recommendation,
    routes,
  };
}
