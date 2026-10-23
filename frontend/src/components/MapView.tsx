import { memo, useEffect, useRef } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import L from "../leafletSetup";
import "leaflet.heat";
import { RISK_COLORS, routeColor } from "../colors";
import { formatMiles, formatWhen, riskLabel } from "../format";
import type { HeatPoint, RouteOption } from "../types";

interface MapViewProps {
  routes: RouteOption[];
  heatPoints: HeatPoint[];
  hour: number;
  showHeat: boolean;
  selectedId: string | null;
  sampleMiles: number;
  onSelect: (id: string) => void;
}

export function MapView({
  routes,
  heatPoints,
  hour,
  showHeat,
  selectedId,
  sampleMiles,
  onSelect,
}: MapViewProps) {
  return (
    <>
    <MapContainer
      center={[39.5, -96]}
      zoom={4}
      preferCanvas
      zoomControl
      className="map"
    >
      <TileLayer
        attribution='&copy; OpenStreetMap contributors &copy; CARTO'
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
      />
      <HeatOverlay points={heatPoints} hour={hour} visible={showHeat && heatPoints.length > 0} />
      <RouteLayer routes={routes} selectedId={selectedId} sampleMiles={sampleMiles} onSelect={onSelect} />
      <FitRoutes routes={routes} />
    </MapContainer>
    <div className="legend">
      {(
        [
          ["low", "Low"],
          ["moderate", "Moderate"],
          ["high", "High"],
          ["severe", "Severe"],
          ["no_travel", "No travel"],
        ] as const
      ).map(([name, label]) => (
        <span key={name}>
          <i style={{ background: RISK_COLORS[name] }} />
          {label}
        </span>
      ))}
    </div>
    </>
  );
}

const RouteLayer = memo(function RouteLayer({
  routes,
  selectedId,
  sampleMiles,
  onSelect,
}: {
  routes: RouteOption[];
  selectedId: string | null;
  sampleMiles: number;
  onSelect: (id: string) => void;
}) {
  const ordered = [...routes].sort((a, b) => Number(a.id === selectedId) - Number(b.id === selectedId));
  const radius = sampleMiles >= 50 ? 7 : sampleMiles >= 25 ? 6 : 5;
  return (
    <>
      {ordered.map((route) => {
        const selected = route.id === selectedId;
        const color = routeColor(route.id);
        return (
          <span key={route.id} style={{ display: "contents" }}>
            <Polyline
              positions={route.geometry}
              pathOptions={{
                color,
                weight: selected ? 6 : 4,
                opacity: selected ? 0.95 : 0.55,
              }}
              eventHandlers={{ click: () => onSelect(route.id) }}
            />
            {route.checkpoints.map((checkpoint) => (
              <CircleMarker
                key={`${route.id}-${checkpoint.distance_miles}`}
                center={[checkpoint.lat, checkpoint.lon]}
                radius={selected ? radius + 1 : radius}
                pathOptions={{
                  color: "#fffaf3",
                  weight: 1.5,
                  fillColor: RISK_COLORS[checkpoint.risk],
                  fillOpacity: selected ? 0.95 : 0.55,
                }}
                eventHandlers={{ click: () => onSelect(route.id) }}
              >
                <Popup>
                  <div className="popup">
                    <p className="popup-title">
                      {route.name} · mile {checkpoint.distance_miles.toFixed(0)}
                    </p>
                    <p>{formatWhen(checkpoint.eta)}</p>
                    <table>
                      <tbody>
                        <tr>
                          <th>Wind</th>
                          <td>
                            {checkpoint.wind_mph.toFixed(1)} mph · {riskLabel(checkpoint.wind_risk_after_load)}
                          </td>
                        </tr>
                        <tr>
                          <th>Rain</th>
                          <td>
                            {checkpoint.rain_in_hr.toFixed(2)} in/hr · {riskLabel(checkpoint.rain_risk)}
                          </td>
                        </tr>
                        <tr>
                          <th>Snow</th>
                          <td>
                            {checkpoint.snow_in_hr.toFixed(2)} in/hr · {riskLabel(checkpoint.snow_risk)}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                    <p className="popup-risk">
                      Checkpoint risk: <strong>{riskLabel(checkpoint.risk)}</strong>
                    </p>
                    {checkpoint.load_note && <p>{checkpoint.load_note}</p>}
                    {checkpoint.missing_weather && (
                      <p>Part of this hour was missing and was treated as zero.</p>
                    )}
                    <p className="popup-mile">{formatMiles(checkpoint.distance_miles)} along the route</p>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </span>
        );
      })}
    </>
  );
});

function HeatOverlay({
  points,
  hour,
  visible,
}: {
  points: HeatPoint[];
  hour: number;
  visible: boolean;
}) {
  const map = useMap();
  const layerRef = useRef<L.Layer & { setLatLngs: (latlngs: Array<[number, number, number?]>) => void; _canvas?: HTMLCanvasElement } | null>(null);
  const pointsRef = useRef(points);
  const hourRef = useRef(hour);
  const visibleRef = useRef(visible);
  pointsRef.current = points;
  hourRef.current = hour;
  visibleRef.current = visible;

  useEffect(() => {
    const layer = L.heatLayer([], {
      radius: 36,
      blur: 32,
      max: 1,
      minOpacity: 0.18,
      maxZoom: 8,
      gradient: {
        0.0: "#1f7a4d",
        0.28: "#7dbe3a",
        0.48: "#e0b000",
        0.68: "#e06a12",
        0.84: "#c4312b",
        1: "#5b2c83",
      },
    });
    layer.addTo(map);
    const overlay = map.getPane("overlayPane");
    if (layer._canvas && overlay && layer._canvas.parentElement === overlay) {
      overlay.insertBefore(layer._canvas, overlay.firstChild);
      layer._canvas.style.pointerEvents = "none";
    }
    layerRef.current = layer;
    draw();
    return () => {
      layer.remove();
      layerRef.current = null;
    };
    // The layer is created once per map. Later hour changes call draw().
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  useEffect(() => {
    draw();
  });

  function draw() {
    const layer = layerRef.current;
    if (!layer) return;
    if (!visibleRef.current) {
      layer.setLatLngs([]);
      return;
    }
    const currentHour = hourRef.current;
    layer.setLatLngs(
      pointsRef.current.map((point) => [point.lat, point.lon, point.intensity[currentHour] ?? 0]),
    );
  }

  return null;
}

function FitRoutes({ routes }: { routes: RouteOption[] }) {
  const map = useMap();
  useEffect(() => {
    if (!routes.length) return;
    const bounds = L.latLngBounds(routes.flatMap((route) => route.geometry));
    if (bounds.isValid()) {
      map.fitBounds(bounds, { paddingTopLeft: [36, 36], paddingBottomRight: [36, 150] });
    }
  }, [routes, map]);
  return null;
}
