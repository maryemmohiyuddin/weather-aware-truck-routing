import L from "leaflet";

// leaflet.heat looks up the global L from the Leaflet 1.x script tag.
const host = window as unknown as { L: typeof L };
host.L = L;

export default L;
