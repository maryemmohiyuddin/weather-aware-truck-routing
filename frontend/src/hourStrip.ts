import type { RiskName } from "./types";

const SCORE: Record<RiskName, number> = {
  low: 1,
  moderate: 2,
  high: 3,
  severe: 4,
  no_travel: 5,
};

export interface HourWeather {
  maxWind: number;
  avgWind: number;
  maxRain: number;
  avgRain: number;
  maxSnow: number;
  avgSnow: number;
  worst: RiskName;
}

type Sample = {
  wind_mph: number;
  rain_in_hr: number;
  snow_in_hr: number;
  risk: RiskName;
};

export function summarizeCheckpoints(checkpoints: Sample[]): HourWeather {
  if (!checkpoints.length) {
    return { maxWind: 0, avgWind: 0, maxRain: 0, avgRain: 0, maxSnow: 0, avgSnow: 0, worst: "low" };
  }
  const count = checkpoints.length;
  let maxWind = 0;
  let maxRain = 0;
  let maxSnow = 0;
  let windSum = 0;
  let rainSum = 0;
  let snowSum = 0;
  let worst: RiskName = "low";
  for (const point of checkpoints) {
    maxWind = Math.max(maxWind, point.wind_mph);
    maxRain = Math.max(maxRain, point.rain_in_hr);
    maxSnow = Math.max(maxSnow, point.snow_in_hr);
    windSum += point.wind_mph;
    rainSum += point.rain_in_hr;
    snowSum += point.snow_in_hr;
    if (SCORE[point.risk] > SCORE[worst]) worst = point.risk;
  }
  return {
    maxWind,
    avgWind: windSum / count,
    maxRain,
    avgRain: rainSum / count,
    maxSnow,
    avgSnow: snowSum / count,
    worst,
  };
}

/** Lowest overall risk, then the least wind. Ties keep the earlier hour. */
export function bestHour(hours: HourWeather[]): number {
  let best = 0;
  for (let index = 1; index < hours.length; index += 1) {
    const score = SCORE[hours[index].worst];
    const bestScore = SCORE[hours[best].worst];
    if (score < bestScore || (score === bestScore && hours[index].maxWind < hours[best].maxWind)) {
      best = index;
    }
  }
  return best;
}

function riskWord(risk: RiskName): string {
  if (risk === "no_travel") return "No travel";
  return risk.charAt(0).toUpperCase() + risk.slice(1);
}

export function hourReadout(when: string, stats: HourWeather): string {
  const wind =
    stats.maxWind < 0.5
      ? "no wind"
      : `wind up to ${Math.round(stats.maxWind)} mph (avg ${Math.round(stats.avgWind)})`;
  const rain =
    stats.maxRain < 0.005
      ? "no rain"
      : `rain up to ${stats.maxRain.toFixed(2)} in/hr (avg ${stats.avgRain.toFixed(2)})`;
  const snow =
    stats.maxSnow < 0.005
      ? "no snow"
      : `snow up to ${stats.maxSnow.toFixed(2)} in/hr (avg ${stats.avgSnow.toFixed(2)})`;
  return `Leaving ${when}: ${wind}, ${rain}, ${snow}, risk ${riskWord(stats.worst)}`;
}
