import assert from "node:assert/strict";
import test from "node:test";
import { bestHour, hourReadout, summarizeCheckpoints } from "./src/hourStrip.ts";

test("a calm hour still reports the wind numbers", () => {
  const stats = summarizeCheckpoints([
    { wind_mph: 10, rain_in_hr: 0, snow_in_hr: 0, risk: "low" },
    { wind_mph: 17, rain_in_hr: 0, snow_in_hr: 0, risk: "low" },
  ]);
  assert.equal(stats.maxWind, 17);
  assert.equal(stats.avgWind, 13.5);
  assert.equal(stats.worst, "low");
  assert.equal(
    hourReadout("Wed 7 AM", stats),
    "Leaving Wed 7 AM: wind up to 17 mph (avg 14), no rain, no snow, risk Low",
  );
});

test("the same risk class still changes the sentence when the wind changes", () => {
  const later = summarizeCheckpoints([
    { wind_mph: 4, rain_in_hr: 0.02, snow_in_hr: 0, risk: "low" },
  ]);
  assert.equal(
    hourReadout("Thu 1 AM", later),
    "Leaving Thu 1 AM: wind up to 4 mph (avg 4), rain up to 0.02 in/hr (avg 0.02), no snow, risk Low",
  );
});

test("the best hour is the calmest, then the least wind", () => {
  const calm = summarizeCheckpoints([{ wind_mph: 8, rain_in_hr: 0, snow_in_hr: 0, risk: "low" }]);
  const windy = summarizeCheckpoints([{ wind_mph: 40, rain_in_hr: 0, snow_in_hr: 0, risk: "high" }]);
  const breezy = summarizeCheckpoints([{ wind_mph: 12, rain_in_hr: 0, snow_in_hr: 0, risk: "low" }]);
  assert.equal(bestHour([windy, breezy, calm]), 2);
  assert.equal(bestHour([breezy, calm]), 1);
});
