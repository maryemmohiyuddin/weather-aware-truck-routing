/** What the forecast slider does.

Hour 0 is the departure in the form. Hour N leaves N hours later.
Play walks one hour at a time and stops on 48. Dragging pauses.
*/

export function nextPlayHour(hour: number, max = 48): number | null {
  if (hour >= max) return null;
  return hour + 1;
}

/** Next checkpoint index, or null when the truck is already on the last one. */
export function nextPlayStop(index: number, last: number): number | null {
  if (last < 0 || index >= last) return null;
  return index + 1;
}

export function departureAt(iso: string, hour: number): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Date(date.getTime() + hour * 3600 * 1000).toISOString();
}
