import { useEffect, useRef, useState } from "react";
import { formatLeaving } from "../format";
import { departureAt, nextPlayHour } from "../playback";

interface ForecastSliderProps {
  departure: string;
  hour: number;
  onHour: (hour: number) => void;
}

export function ForecastSlider({ departure, hour, onHour }: ForecastSliderProps) {
  const [playing, setPlaying] = useState(false);
  const hourRef = useRef(hour);
  hourRef.current = hour;
  const leaving = formatLeaving(departureAt(departure, hour));

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

  return (
    <div className="forecast">
      <div className="forecast-top">
        <p className="leaving">
          Leaving <strong>{leaving}</strong>
        </p>
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
      <div className="forecast-readout">
        <strong>
          Hour {hour} of 48
        </strong>
        <span>{hour === 0 ? "the typed departure" : `${hour} hour${hour === 1 ? "" : "s"} later`}</span>
      </div>
      <input
        type="range"
        min={0}
        max={48}
        step={1}
        value={hour}
        aria-label="Hours later to leave"
        aria-valuetext={`Leaving ${leaving}`}
        onPointerDown={() => setPlaying(false)}
        onChange={(event) => {
          setPlaying(false);
          onHour(Number(event.target.value));
        }}
      />
      <p className="forecast-note">
        Moving this leaves later. Arrivals and risk use the forecast already loaded. It does not call the server.
      </p>
    </div>
  );
}
