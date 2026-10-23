import { RISK_COLORS, routeColor } from "../colors";
import { formatDuration, formatMiles, riskLabel } from "../format";
import type { Plan, RiskName } from "../types";

const SEGMENTS: RiskName[] = ["low", "moderate", "high", "severe", "no_travel"];

interface RouteListProps {
  plan: Plan;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function RouteList({ plan, selectedId, onSelect }: RouteListProps) {
  return (
    <section className="results">
      <div className="recommendation">
        <p className="eyebrow">Recommended</p>
        <p>{plan.recommendation.summary}</p>
        <p className="order-note">
          Checked in order: fewest no-travel miles, fewest severe miles, fewest high miles, lowest
          average risk, shortest time. No-travel is worse than severe.
        </p>
      </div>
      <ul className="route-list">
        {plan.routes.map((route) => {
          const total =
            route.miles.low +
            route.miles.moderate +
            route.miles.high +
            route.miles.severe +
            route.miles.no_travel;
          return (
            <li key={route.id}>
              <button
                type="button"
                className={route.id === selectedId ? "route-card selected" : "route-card"}
                style={{ borderLeftColor: routeColor(route.id) }}
                onClick={() => onSelect(route.id)}
              >
                <div className="route-top">
                  <strong>{route.name}</strong>
                  {route.recommended && <span className="badge">Recommended</span>}
                </div>
                <p className="route-meta">
                  {route.via_label ? `via ${route.via_label}` : "local roads"}
                  {" · "}
                  {route.source === "via" ? "via point" : "OSRM"}
                </p>
                <p className="route-stats">
                  <span>{formatMiles(route.distance_miles)}</span>
                  <span>{formatDuration(route.duration_seconds)}</span>
                </p>
                <dl className="mile-grid">
                  <div>
                    <dt>No travel</dt>
                    <dd>{formatMiles(route.miles.no_travel)}</dd>
                  </div>
                  <div>
                    <dt>Severe</dt>
                    <dd>{formatMiles(route.miles.severe)}</dd>
                  </div>
                  <div>
                    <dt>High</dt>
                    <dd>{formatMiles(route.miles.high)}</dd>
                  </div>
                  <div>
                    <dt>Avg risk</dt>
                    <dd>{route.average_risk.toFixed(2)}</dd>
                  </div>
                </dl>
                {total > 0 && (
                  <div className="risk-bar" aria-hidden="true">
                    {SEGMENTS.map((name) => {
                      const miles = route.miles[name];
                      if (miles <= 0) return null;
                      return (
                        <span
                          key={name}
                          style={{ width: `${(miles / total) * 100}%`, background: RISK_COLORS[name] }}
                          title={`${riskLabel(name)} ${formatMiles(miles)}`}
                        />
                      );
                    })}
                  </div>
                )}
              </button>
            </li>
          );
        })}
      </ul>
      <p className="routing-note">{plan.routing.note}</p>
    </section>
  );
}
