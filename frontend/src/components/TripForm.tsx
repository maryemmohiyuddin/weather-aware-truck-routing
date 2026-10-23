import type { Place } from "../types";
import { PlaceField } from "./PlaceField";

export const EXAMPLES: {
  label: string;
  origin: Place;
  destination: Place;
  weight: string;
}[] = [
  {
    label: "Chicago → New York",
    origin: { label: "Chicago, Illinois, United States", lat: 41.8781, lon: -87.6298 },
    destination: { label: "New York, New York, United States", lat: 40.7128, lon: -74.006 },
    weight: "42000",
  },
  {
    label: "Dallas → Atlanta",
    origin: { label: "Dallas, Texas, United States", lat: 32.7767, lon: -96.797 },
    destination: { label: "Atlanta, Georgia, United States", lat: 33.749, lon: -84.388 },
    weight: "28000",
  },
];

interface TripFormProps {
  origin: Place | null;
  destination: Place | null;
  departure: string;
  weight: string;
  loading: boolean;
  onOrigin: (place: Place | null) => void;
  onDestination: (place: Place | null) => void;
  onDeparture: (value: string) => void;
  onWeight: (value: string) => void;
  onSubmit: () => void;
  onExample: (example: (typeof EXAMPLES)[number]) => void;
}

export function TripForm({
  origin,
  destination,
  departure,
  weight,
  loading,
  onOrigin,
  onDestination,
  onDeparture,
  onWeight,
  onSubmit,
  onExample,
}: TripFormProps) {
  return (
    <form
      className="trip-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <PlaceField label="Origin" placeholder="City or address" place={origin} onChange={onOrigin} />
      <PlaceField
        label="Destination"
        placeholder="City or address"
        place={destination}
        onChange={onDestination}
      />
      <div className="field-row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            value={departure}
            onChange={(event) => onDeparture(event.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="weight">Load (lb)</label>
          <input
            id="weight"
            inputMode="decimal"
            value={weight}
            onChange={(event) => onWeight(event.target.value)}
            required
          />
        </div>
      </div>
      <button className="compare" type="submit" disabled={loading}>
        {loading ? "Comparing routes…" : "Compare routes"}
      </button>
      <div className="examples">
        <span>Try</span>
        {EXAMPLES.map((example) => (
          <button key={example.label} type="button" onClick={() => onExample(example)} disabled={loading}>
            {example.label}
          </button>
        ))}
      </div>
    </form>
  );
}
