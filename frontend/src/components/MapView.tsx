import { Fragment, memo, useEffect, useRef } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import L from "../leafletSetup";
import { RISK_COLORS, routeColor } from "../colors";
import { formatMiles, formatWhen, riskLabel } from "../format";
import type { RouteOption } from "../types";

interface MapViewProps {
  routes: RouteOption[];
  selectedId: string | null;
  sampleMiles: number;
  dataToken: string;
  onSelect: (id: string) => void;
}

const BASEMAP =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}";
const LABELS =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}";

export function MapView({ routes, selectedId, sampleMiles, dataToken, onSelect }: MapViewProps) {
  return (
    <>
    <MapContainer
      center={[39.5, -96]}
      zoom={4}
      zoomControl={false}
      className="map"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.esri.com/">Esri</a>, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url={BASEMAP}
        tileSize={256}
        maxZoom={16}
        maxNativeZoom={16}
        detectRetina={false}
      />
      <TileLayer url={LABELS} tileSize={256} maxZoom={16} maxNativeZoom={16} detectRetina={false} />
      <ClosePopups token={dataToken} />
      <FitSize />
      <ZoomButtons />
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
          <Fragment key={route.id}>
            <RouteStroke
              positions={route.geometry}
              selected={selected}
              color={color}
              onClick={() => onSelect(route.id)}
            />
            {selected && route.checkpoints.map((checkpoint) => (
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
          </Fragment>
        );
      })}
    </>
  );
});

function RouteStroke({
  positions,
  selected,
  color,
  onClick,
}: {
  positions: [number, number][];
  selected: boolean;
  color: string;
  onClick: () => void;
}) {
  const casingRef = useRef<L.Polyline | null>(null);
  const lineRef = useRef<L.Polyline | null>(null);
  useEffect(() => {
    if (!selected) return;
    casingRef.current?.bringToFront();
    lineRef.current?.bringToFront();
  }, [selected, positions]);
  return (
    <>
      {selected && (
        <Polyline
          ref={casingRef}
          positions={positions}
          pathOptions={{
            color: "#f4f0e8",
            weight: 14,
            opacity: 1,
            lineCap: "round",
            lineJoin: "round",
          }}
        />
      )}
      <Polyline
        ref={lineRef}
        positions={positions}
        pathOptions={{
          color,
          weight: selected ? 7 : 3,
          opacity: selected ? 1 : 0.35,
          lineCap: "round",
          lineJoin: "round",
        }}
        eventHandlers={{ click: onClick }}
      />
    </>
  );
}

function ZoomButtons() {
  const map = useMap();
  return (
    <div className="leaflet-top leaflet-left">
      <div className="leaflet-control zoom-pad" role="group" aria-label="Map zoom">
        <button type="button" title="Zoom in" aria-label="Zoom in" onClick={() => map.zoomIn()}>
          Zoom in
        </button>
        <button type="button" title="Zoom out" aria-label="Zoom out" onClick={() => map.zoomOut()}>
          Zoom out
        </button>
      </div>
    </div>
  );
}

function ClosePopups({ token }: { token: string }) {
  const map = useMap();
  useEffect(() => {
    map.closePopup();
  }, [map, token]);
  return null;
}

function FitSize() {
  const map = useMap();
  useEffect(() => {
    const frame = requestAnimationFrame(() => map.invalidateSize());
    return () => cancelAnimationFrame(frame);
  }, [map]);
  return null;
}

function FitRoutes({ routes }: { routes: RouteOption[] }) {
  const map = useMap();
  const routesRef = useRef(routes);
  routesRef.current = routes;
  const fitKey = routes.map((route) => `${route.id}:${route.geometry.length}`).join("|");
  useEffect(() => {
    const current = routesRef.current;
    if (!current.length) return;
    const bounds = L.latLngBounds(current.flatMap((route) => route.geometry));
    if (bounds.isValid()) {
      map.fitBounds(bounds, { paddingTopLeft: [36, 36], paddingBottomRight: [36, 210] });
    }
  }, [fitKey, map]);
  return null;
}
