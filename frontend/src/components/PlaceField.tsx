import { useEffect, useId, useRef, useState } from "react";
import { searchPlaces } from "../api";
import type { Place } from "../types";

interface PlaceFieldProps {
  label: string;
  placeholder: string;
  place: Place | null;
  onChange: (place: Place | null) => void;
}

export function PlaceField({ label, placeholder, place, onChange }: PlaceFieldProps) {
  const inputId = useId();
  const listId = useId();
  const [text, setText] = useState(place?.label ?? "");
  const [results, setResults] = useState<Place[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [status, setStatus] = useState("");
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (place) setText(place.label);
  }, [place]);

  useEffect(() => {
    if (place && text === place.label) {
      setResults([]);
      setOpen(false);
      return;
    }
    const query = text.trim();
    if (query.length < 2) {
      setResults([]);
      setStatus("");
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setStatus("Searching…");
      searchPlaces(query, controller.signal)
        .then((found) => {
          setResults(found);
          setActive(0);
          setOpen(true);
          setStatus(found.length ? "" : "No matches");
        })
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === "AbortError") return;
          setResults([]);
          setStatus("Place search is unavailable");
          setOpen(true);
        });
    }, 300);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [text, place]);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  function choose(next: Place) {
    onChange(next);
    setText(next.label);
    setOpen(false);
    setResults([]);
  }

  return (
    <div className="field" ref={boxRef}>
      <label htmlFor={inputId}>{label}</label>
      <input
        id={inputId}
        role="combobox"
        aria-expanded={open && results.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        placeholder={placeholder}
        value={text}
        autoComplete="off"
        onChange={(event) => {
          setText(event.target.value);
          onChange(null);
          setOpen(true);
        }}
        onFocus={() => {
          if (results.length) setOpen(true);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setOpen(true);
            setActive((index) => Math.min(index + 1, Math.max(results.length - 1, 0)));
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setActive((index) => Math.max(index - 1, 0));
          } else if (event.key === "Enter" && open && results[active]) {
            event.preventDefault();
            choose(results[active]);
          } else if (event.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {open && (results.length > 0 || status) && (
        <ul id={listId} role="listbox" className="suggestions">
          {results.map((result, index) => (
            <li key={`${result.label}-${result.lat}-${result.lon}`}>
              <button
                type="button"
                role="option"
                aria-selected={index === active}
                onMouseEnter={() => setActive(index)}
                onClick={() => choose(result)}
              >
                {result.label}
              </button>
            </li>
          ))}
          {results.length === 0 && status && <li className="suggestion-status">{status}</li>}
        </ul>
      )}
    </div>
  );
}
