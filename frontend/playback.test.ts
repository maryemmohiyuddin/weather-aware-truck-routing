import assert from "node:assert/strict";
import test from "node:test";
import { departureAt, nextPlayHour } from "./src/playback.ts";

test("play advances one hour and stops at the end", () => {
  assert.equal(nextPlayHour(0), 1);
  assert.equal(nextPlayHour(47), 48);
  assert.equal(nextPlayHour(48), null);
});

test("leaving later moves the departure by whole hours", () => {
  assert.equal(departureAt("2026-10-27T22:00:00.000Z", 0), "2026-10-27T22:00:00.000Z");
  assert.equal(departureAt("2026-10-27T22:00:00.000Z", 4), "2026-10-28T02:00:00.000Z");
});
