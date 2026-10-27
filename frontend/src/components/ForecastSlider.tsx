import { useEffect, useRef, useState } from "react";
import { RISK_COLORS } from "../colors";
import { formatWhen, riskLabel } from "../format";
import type { HourWeather } from "../hourStrip";
import { nextPlayHour, nextPlayStop } from "../playback";
import type { RiskName } from "../types";

export interface TruckStop {
  index: number;
  count: number;
  mile: number;
  eta: string;
  wind: number;
  rain: number;
  snow: number;
  risk: RiskName;
}

interface ForecastSliderProps {
  hour: number;
  readout: string;
  strip: HourWeather[];
  bestHourIndex: number;
  bestLabel: string;
  onHour: (hour: number) => void;
  truck: TruckStop | null;
  onStop: (index: number) => void;
}

export function ForecastSlider({
  hour,
  readout,
  strip,
  bestHourIndex,
  bestLabel,
  onHour,
  truck,
  onStop,
}: ForecastSliderProps) {
  const [playing, setPlaying] = useState<"hours" | "trip" | null>(null);
  const hourRef = useRef(hour);
  const stopRef = useRef(truck?.index ?? 0);
  const lastStopRef = useRef(Math.max(0, (truck?.count ?? 1) - 1));
  hourRef.current = hour;
  stopRef.current = truck?.index ?? 0;
  lastStopRef.current = Math.max(0, (truck?.count ?? 1) - 1);
  const peak = Math.max(1, ...strip.map((item) => item.maxWind));

  useEffect(() => {
    if (playing !== "hours") return;
    const id = window.setInterval(() => {
      const next = nextPlayHour(hourRef.current);
      if (next === null) {
        setPlaying(null);
        return;
      }
      onHour(next);
    }, 700);
    return () => window.clearInterval(id);
  }, [playing, onHour]);

  useEffect(() => {
    if (playing !== "trip") return;
    const id = window.setInterval(() => {
      const next = nextPlayStop(stopRef.current, lastStopRef.current);
      if (next === null) {
        setPlaying(null);
        return;
      }
      onStop(next);
    }, 400);
    return () => window.clearInterval(id);
  }, [playing, onStop]);

  function pickHour(next: number) {
    setPlaying(null);
    onHour(next);
  }

  function pickStop(next: number) {
    setPlaying(null);
    onStop(next);
  }

  return (
    <div className="forecast">
      <p className="forecast-caption">
        Move the slider to see what the weather would be like if the truck left later.
      </p>
      <div className="forecast-top">
        <p className="leaving-readout">{readout}</p>
        <button
          type="button"
          className="play"
          onClick={() => {
            if (playing === "hours") {
              setPlaying(null);
              return;
            }
            if (nextPlayHour(hour) === null) onHour(0);
            setPlaying("hours");
          }}
        >
          {playing === "hours" ? "Pause" : "Play hours"}
        </button>
      </div>
      {strip.length > 0 && (
        <div className="hour-strip" role="group" aria-label="Departure hours for the selected route">
          {strip.map((item, index) => (
            <button
              key={index}
              type="button"
              className={index === hour ? "on" : undefined}
              style={{
                height: `${8 + (item.maxWind / peak) * 30}px`,
                background: RISK_COLORS[item.worst],
              }}
              aria-current={index === hour ? "true" : undefined}
              aria-label={`Hour ${index}, wind up to ${Math.round(item.maxWind)} mph, risk ${riskLabel(item.worst)}${index === bestHourIndex ? ", best time to leave" : ""}`}
              onClick={() => pickHour(index)}
            >
              {index === bestHourIndex && <span className="best-pip" aria-hidden="true" />}
            </button>
          ))}
        </div>
      )}
      <input
        type="range"
        min={0}
        max={48}
        step={1}
        value={hour}
        aria-label="Hours later to leave"
        aria-valuetext={readout}
        onPointerDown={() => setPlaying(null)}
        onChange={(event) => pickHour(Number(event.target.value))}
      />
      {strip.length > 0 && <p className="best-leave">Best time to leave: {bestLabel}</p>}
      {truck && truck.count > 0 && (
        <div className="truck-controls">
          <div className="forecast-top">
            <p className="truck-label">Truck position</p>
            <button
              type="button"
              className="play"
              onClick={() => {
                if (playing === "trip") {
                  setPlaying(null);
                  return;
                }
                if (nextPlayStop(truck.index, truck.count - 1) === null) onStop(0);
                setPlaying("trip");
              }}
            >
              {playing === "trip" ? "Pause" : "Play trip"}
            </button>
          </div>
          <div className="truck-step">
            <button
              type="button"
              className="play"
              aria-label="Previous checkpoint"
              disabled={truck.index <= 0}
              onClick={() => pickStop(Math.max(0, truck.index - 1))}
            >
              Prev
            </button>
            <input
              type="range"
              min={0}
              max={Math.max(0, truck.count - 1)}
              step={1}
              value={truck.index}
              aria-label="Truck position"
              aria-valuetext={`Checkpoint ${truck.index + 1} of ${truck.count}, mile ${truck.mile.toFixed(0)}`}
              onPointerDown={() => setPlaying(null)}
              onChange={(event) => pickStop(Number(event.target.value))}
            />
            <button
              type="button"
              className="play"
              aria-label="Next checkpoint"
              disabled={truck.index >= truck.count - 1}
              onClick={() => pickStop(Math.min(truck.count - 1, truck.index + 1))}
            >
              Next
            </button>
          </div>
          <div className="truck-card">
            <p>
              <strong>
                Checkpoint {truck.index + 1} of {truck.count}
              </strong>
              {" · "}
              mile {truck.mile.toFixed(0)}
            </p>
            <p>Arrives {formatWhen(truck.eta)}</p>
            <p>
              Wind {truck.wind.toFixed(0)} mph · rain {truck.rain.toFixed(2)} in/hr · snow {truck.snow.toFixed(2)} in/hr
            </p>
            <p className="truck-risk">
              <i style={{ background: RISK_COLORS[truck.risk] }} />
              {riskLabel(truck.risk)}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
