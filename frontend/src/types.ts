export type RiskName = "low" | "moderate" | "high" | "severe" | "no_travel";

export interface Place {
  label: string;
  lat: number;
  lon: number;
}

export interface Checkpoint {
  lat: number;
  lon: number;
  distance_miles: number;
  eta: string;
  wind_mph: number;
  rain_in_hr: number;
  snow_in_hr: number;
  wind_risk: RiskName;
  wind_risk_after_load: RiskName;
  rain_risk: RiskName;
  snow_risk: RiskName;
  risk: RiskName;
  load_adjusted: boolean;
  load_note: string | null;
  missing_weather: boolean;
}

export interface RouteOption {
  id: string;
  name: string;
  source: "osrm" | "via";
  via_label: string | null;
  via: { lat: number; lon: number } | null;
  distance_miles: number;
  duration_seconds: number;
  geometry: [number, number][];
  checkpoints: Checkpoint[];
  miles: {
    no_travel: number;
    severe: number;
    high: number;
    moderate: number;
    low: number;
  };
  average_risk: number;
  rank: number;
  recommended: boolean;
}

export interface HeatPoint {
  lat: number;
  lon: number;
  intensity: number[];
}

export interface Plan {
  origin: Place;
  destination: Place;
  departure: string;
  load_weight_lb: number;
  sample_miles: 10 | 25 | 50;
  routing: {
    provider: string;
    osrm_routes: number;
    via_routes: number;
    note: string;
  };
  recommendation: {
    route_id: string | null;
    summary: string;
  };
  routes: RouteOption[];
  heatmap: {
    base_time: string;
    hours: number;
    points: HeatPoint[];
  };
  risk_scale: Record<string, number>;
}

export interface PlanRequest {
  origin: Place;
  destination: Place;
  departure: string;
  load_weight_lb: number;
  sample_miles: 10 | 25 | 50;
}
