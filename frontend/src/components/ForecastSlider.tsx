import { useEffect, useRef, useState } from "react";
import { RISK_COLORS } from "../colors";
import { riskLabel } from "../format";
import type { HourWeather } from "../hourStrip";
import { nextPlayHour } from "../playback";

interface ForecastSliderProps {
  hour: number;
  readout: string;
  strip: HourWeather[];
  bestHourIndex: number;
  bestLabel: string;
  onHour: (hour: number) => void;
}

export function ForecastSlider({
  hour,
  readout,
  strip,
  bestHourIndex,
  bestLabel,
  onHour,
}: ForecastSliderProps) {
  const [playing, setPlaying] = useState(false);
  const hourRef = useRef(hour);
  hourRef.current = hour;
  const peak = Math.max(1, ...strip.map((item) => item.maxWind));

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      const next = nextPlayHour(hourRef.current);
      if (next === null) {
        setPlaying(false);
        return;
      }
      onHour(next);
    }, 700);
    return () => window.clearInterval(id);
  }, [playing, onHour]);

  function pick(next: number) {
    setPlaying(false);
    onHour(next);
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
            if (playing) {
              setPlaying(false);
              return;
            }
            if (nextPlayHour(hour) === null) onHour(0);
            setPlaying(true);
          }}
        >
          {playing ? "Pause" : "Play"}
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
              onClick={() => pick(index)}
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
        onPointerDown={() => setPlaying(false)}
        onChange={(event) => pick(Number(event.target.value))}
      />
      {strip.length > 0 && <p className="best-leave">Best time to leave: {bestLabel}</p>}
    </div>
  );
}
