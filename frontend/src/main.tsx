import { createRoot } from "react-dom/client";
import "@fontsource/source-sans-3/400.css";
import "@fontsource/source-sans-3/600.css";
import "@fontsource/source-serif-4/600.css";
import "leaflet/dist/leaflet.css";
import { App } from "./App";
import "./styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("missing root");
// Leaflet does not like React StrictMode's double mount, so the app is rendered once.
createRoot(root).render(<App />);
