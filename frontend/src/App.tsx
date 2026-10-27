import { useCallback, useRef, useState } from "react";
import { requestPlan } from "./api";
import { ForecastSlider } from "./components/ForecastSlider";
import { MapView } from "./components/MapView";
import { RouteList } from "./components/RouteList";
import { Rules } from "./components/Rules";
import { TripForm } from "./components/TripForm";
import { defaultDepartureValue, formatBestLeave, formatHourClock, localInputToIso } from "./format";
import { bestHour, hourReadout, summarizeCheckpoints } from "./hourStrip";
import { departureAt } from "./playback";
import { planAtHour } from "./timeline";
import type { Place, Plan } from "./types";

type SampleMiles = 10 | 25 | 50;

export function App() {
  const [origin, setOrigin] = useState<Place | null>(null);
  const [destination, setDestination] = useState<Place | null>(null);
  const [departure, setDeparture] = useState(defaultDepartureValue);
  const [weight, setWeight] = useState("35000");
  const [sampleMiles, setSampleMiles] = useState<SampleMiles>(25);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hour, setHour] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef({ origin, destination, departure, weight, sampleMiles });
  latest.current = { origin, destination, departure, weight, sampleMiles };
  const requestId = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const searched = useRef(false);

  const run = useCallback(async (overrides?: Partial<{ origin: Place | null; destination: Place | null; weight: string; sampleMiles: SampleMiles }>) => {
    const current = { ...latest.current, ...overrides };
    if (!current.origin || !current.destination) {
      setError("Choose an origin and a destination from the suggestions.");
      setPlan(null);
      return;
    }
    const load = Number(current.weight);
    if (!Number.isFinite(load) || load < 0) {
      setError("Enter the load weight in pounds.");
      setPlan(null);
      return;
    }
    let departureIso: string;
    try {
      departureIso = localInputToIso(current.departure);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Choose a valid departure time.");
      setPlan(null);
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const next = await requestPlan(
        {
          origin: current.origin,
          destination: current.destination,
          departure: departureIso,
          load_weight_lb: load,
          sample_miles: current.sampleMiles,
        },
        controller.signal,
      );
      if (requestId.current !== id) return;
      searched.current = true;
      setPlan(next);
      setSelectedId(next.recommendation.route_id);
      setHour(0);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      if (requestId.current !== id) return;
      setPlan(null);
      setSelectedId(null);
      setError(err instanceof Error ? err.message : "Could not build routes.");
    } finally {
      if (requestId.current === id) setLoading(false);
    }
  }, []);

  function changeSample(next: SampleMiles) {
    setSampleMiles(next);
    if (searched.current) void run({ sampleMiles: next });
  }

  const shown = plan ? planAtHour(plan, hour) : null;
  const routeId =
    selectedId ?? shown?.recommendation.route_id ?? shown?.routes[0]?.id ?? null;
  const selectedRoute = shown?.routes.find((route) => route.id === routeId) ?? null;
  const strip = (plan?.timeline ?? []).map((frame) => {
    const snap = frame.routes.find((route) => route.id === routeId);
    return summarizeCheckpoints(snap?.checkpoints ?? []);
  });
  const stats = summarizeCheckpoints(selectedRoute?.checkpoints ?? []);
  const readout = plan
    ? hourReadout(formatHourClock(departureAt(plan.departure, hour)), stats)
    : "";
  const bestIndex = strip.length ? bestHour(strip) : 0;
  const bestLabel = plan ? formatBestLeave(departureAt(plan.departure, bestIndex)) : "";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" width="28" height="28">
              <path d="M6 22c6-2 8-10 10-14 2 6 6 12 12 14" fill="none" stroke="currentColor" strokeWidth="2" />
              <circle cx="16" cy="8" r="2.2" fill="currentColor" />
              <circle cx="8" cy="22" r="2" />
              <circle cx="24" cy="22" r="2" />
            </svg>
          </span>
          <div>
            <h1>Weather-Aware Truck Routing</h1>
            <p>Three routes, sampled on the truck&apos;s ETA, ranked by weather and time.</p>
          </div>
        </div>
        <div className="interval" role="group" aria-label="Sample every">
          <span>Sample every</span>
          {([10, 25, 50] as SampleMiles[]).map((miles) => (
            <button
              key={miles}
              type="button"
              aria-pressed={sampleMiles === miles}
              onClick={() => changeSample(miles)}
            >
              {miles} mi
            </button>
          ))}
        </div>
      </header>
      <div className="shell">
        <aside className="sidebar">
          <TripForm
            origin={origin}
            destination={destination}
            departure={departure}
            weight={weight}
            loading={loading}
            onOrigin={setOrigin}
            onDestination={setDestination}
            onDeparture={setDeparture}
            onWeight={setWeight}
            onSubmit={() => void run()}
            onExample={(example) => {
              setOrigin(example.origin);
              setDestination(example.destination);
              setWeight(example.weight);
              void run({
                origin: example.origin,
                destination: example.destination,
                weight: example.weight,
              });
            }}
          />
          {loading && (
            <p className="status">
              {plan ? "Updating the sample. The cards below are the previous result." : "Fetching routes and the forecast…"}
            </p>
          )}
          {error && <p className="error">{error}</p>}
          {shown && (
            <div className={loading ? "stale" : undefined}>
              <RouteList plan={shown} selectedId={selectedId} onSelect={setSelectedId} />
            </div>
          )}
          <Rules />
        </aside>
        <main className="map-wrap">
          <MapView
            routes={shown?.routes ?? []}
            selectedId={selectedId}
            sampleMiles={plan?.sample_miles ?? sampleMiles}
            dataToken={`${plan?.departure ?? ""}-${plan?.sample_miles ?? ""}`}
            onSelect={setSelectedId}
          />
          {!plan && !loading && (
            <div className="empty-map">Enter a trip, or try Chicago to New York.</div>
          )}
          {plan && shown && (
            <ForecastSlider
              key={`${plan.departure}-${plan.sample_miles}`}
              hour={hour}
              readout={readout}
              strip={strip}
              bestHourIndex={bestIndex}
              bestLabel={bestLabel}
              onHour={setHour}
            />
          )}
        </main>
      </div>
    </div>
  );
}
