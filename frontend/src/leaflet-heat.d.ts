import * as L from "leaflet";

declare module "leaflet" {
  function heatLayer(
    latlngs: Array<[number, number, number?]>,
    options?: {
      radius?: number;
      blur?: number;
      max?: number;
      minOpacity?: number;
      maxZoom?: number;
      gradient?: Record<number, string>;
    },
  ): HeatLayer;
}

interface HeatLayer extends L.Layer {
  setLatLngs(latlngs: Array<[number, number, number?]>): this;
  redraw(): this;
  _canvas?: HTMLCanvasElement;
}
