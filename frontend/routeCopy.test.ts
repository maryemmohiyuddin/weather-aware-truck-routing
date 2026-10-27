import assert from "node:assert/strict";
import test from "node:test";
import { averageRiskClass, stopsLayerKey, stretchSummary } from "./src/routeCopy.ts";

test("a calm route says there are no risky stretches", () => {
  assert.equal(
    stretchSummary({ no_travel: 0, severe: 0, high: 0 }),
    "No risky stretches on this route",
  );
});

test("risky miles are listed in plain words", () => {
  assert.equal(
    stretchSummary({ no_travel: 0, severe: 12, high: 30.2 }),
    "12 mi severe, 30.2 mi high",
  );
  assert.equal(
    stretchSummary({ no_travel: 8, severe: 0, high: 0 }),
    "8 mi no-travel",
  );
});

test("average risk 1.00 is Low", () => {
  assert.equal(averageRiskClass(1), "low");
  assert.equal(averageRiskClass(1.4), "low");
  assert.equal(averageRiskClass(2.6), "high");
});

test("resampling changes the checkpoint layer key", () => {
  assert.notEqual(stopsLayerKey("A", 25, 40), stopsLayerKey("A", 50, 20));
  assert.notEqual(stopsLayerKey("A", 25, 40), stopsLayerKey("A", 10, 100));
  assert.equal(stopsLayerKey("A", 25, 40), stopsLayerKey("A", 25, 40));
});
