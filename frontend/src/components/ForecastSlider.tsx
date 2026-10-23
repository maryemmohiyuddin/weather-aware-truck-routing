import { useEffect, useRef, useState } from "react";
import { formatForecastStamp } from "../format";

interface ForecastSliderProps {
  baseTime: string;
  hour: number;
  visible: boolean;
  onHour: (hour: number) => void;
  onVisible: (visible: boolean) => void;
}

export function ForecastSlider({ baseTime, hour, visible, onHour, onVisible }: ForecastSliderProps) {
  const [playing, setPlaying] = useState(false);
  const hourRef = useRef(hour);
  hourRef.current = hour;

  useEffect(() => {
    setPlaying(false);
  }, [baseTime]);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      const next = hourRef.current >= 48 ? 0 : hourRef.current + 1;
      onHour(next);
    }, 420);
    return () => window.clearInterval(id);
  }, [playing, onHour]);

  return (
    <div className="forecast">
      <div className="forecast-top">
        <label className="check">
          <input type="checkbox" checked={visible} onChange={(event) => onVisible(event.target.checked)} />
          Corridor forecast
        </label>
        <button
          type="button"
          className="play"
          onClick={() => setPlaying((value) => !value)}
          disabled={!visible}
        >
          {playing ? "Pause" : "Play"}
        </button>
      </div>
      <div className="forecast-readout">
        <strong>
          Hour {hour} of 48
        </strong>
        <span>{formatForecastStamp(baseTime, hour)}</span>
      </div>
      <input
        type="range"
        min={0}
        max={48}
        step={1}
        value={hour}
        disabled={!visible}
        aria-label="Forecast hour"
        aria-valuetext={`Hour ${hour}, ${formatForecastStamp(baseTime, hour)}`}
        onChange={(event) => {
          setPlaying(false);
          onHour(Number(event.target.value));
        }}
      />
      <p className="forecast-note">Loaded with the trip. Dragging the slider does not call the server.</p>
    </div>
  );
}
